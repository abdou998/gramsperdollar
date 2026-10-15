// Grams per Dollar Worker.
// Everything is served as static files from dist/, except /api/*, which runs here.
// /api/* powers the private writing page (/write): log in with a password, send a recipe,
// and the recipe + photos land in the GitHub repo under submissions/ as one commit.
// Nothing is published automatically; prices and nutrition get added before a recipe goes live.
//
// Secrets (Cloudflare dashboard → Worker → Settings → Variables and Secrets):
//   WRITER_PASSWORD  the password for /write
//   GITHUB_TOKEN     fine-grained token, this repo only, "Contents: Read and write"

interface Env {
  ASSETS: { fetch: (req: Request) => Promise<Response> };
  WRITER_PASSWORD?: string;
  GITHUB_TOKEN?: string;
  GITHUB_REPO: string;
  GITHUB_BRANCH: string;
  GITHUB_API?: string; // override for local testing only
}

const COOKIE = 'gpd_writer';
const SESSION_DAYS = 30;
const MAX_PHOTOS = 6;
const MAX_PHOTO_BYTES = 4 * 1024 * 1024;
const MEALS = ['breakfast', 'lunch', 'dinner', 'snack'];

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(request);
    try {
      if (url.pathname === '/api/session' && request.method === 'GET') return session(request, env);
      if (url.pathname === '/api/login' && request.method === 'POST') return login(request, env);
      if (url.pathname === '/api/logout' && request.method === 'POST') return logout();
      if (url.pathname === '/api/submit' && request.method === 'POST') return submit(request, env);
      return json({ error: 'Not found.' }, 404);
    } catch (e) {
      console.error(e);
      return json({ error: 'Something went wrong on our side. Your writing is still saved on this device. Try again in a minute.' }, 500);
    }
  },
};

// ---------- auth ----------

async function hmac(key: string, msg: string): Promise<string> {
  const k = await crypto.subtle.importKey('raw', new TextEncoder().encode(key), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', k, new TextEncoder().encode(msg));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function sameText(a: string, b: string): Promise<boolean> {
  // Compare via HMAC so timing doesn't leak how much of the password matched.
  const [x, y] = await Promise.all([hmac('cmp', a), hmac('cmp', b)]);
  return x === y;
}

async function makeToken(env: Env): Promise<string> {
  const exp = Date.now() + SESSION_DAYS * 864e5;
  return `${exp}.${await hmac(env.WRITER_PASSWORD!, String(exp))}`;
}

async function loggedIn(request: Request, env: Env): Promise<boolean> {
  if (!env.WRITER_PASSWORD) return false;
  const raw = (request.headers.get('Cookie') ?? '').split(/;\s*/).find((c) => c.startsWith(`${COOKIE}=`));
  if (!raw) return false;
  const [exp, sig] = raw.slice(COOKIE.length + 1).split('.');
  if (!exp || !sig || Number(exp) < Date.now()) return false;
  return sameText(sig, await hmac(env.WRITER_PASSWORD, exp));
}

const cookie = (value: string, maxAge: number) =>
  `${COOKIE}=${value}; Path=/api; HttpOnly; Secure; SameSite=Strict; Max-Age=${maxAge}`;

async function session(request: Request, env: Env) {
  return json({ loggedIn: await loggedIn(request, env), configured: Boolean(env.WRITER_PASSWORD && env.GITHUB_TOKEN) });
}

async function login(request: Request, env: Env) {
  if (!env.WRITER_PASSWORD) return json({ error: 'The writing page isn’t set up yet (no password saved on the server).' }, 503);
  const { password } = (await request.json().catch(() => ({}))) as { password?: string };
  await new Promise((r) => setTimeout(r, 400)); // slows down guessing
  if (!password || !(await sameText(password, env.WRITER_PASSWORD))) return json({ error: 'That password didn’t work. Check it and try again.' }, 401);
  return json({ ok: true }, 200, { 'Set-Cookie': cookie(await makeToken(env), SESSION_DAYS * 86400) });
}

function logout() {
  return json({ ok: true }, 200, { 'Set-Cookie': cookie('', 0) });
}

// ---------- submit ----------

const clean = (v: FormDataEntryValue | null, max = 5000) => String(v ?? '').replace(/\r\n/g, '\n').trim().slice(0, max);
const lines = (s: string) => s.split('\n').map((l) => l.replace(/^\s*(?:[-*•]|\d+[.)])\s*/, '').trim()).filter(Boolean);
const slugify = (s: string) => s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'recipe';
const yamlStr = (s: string) => JSON.stringify(s); // JSON strings are valid YAML

async function submit(request: Request, env: Env) {
  if (!(await loggedIn(request, env))) return json({ error: 'You’ve been logged out. Log in again; your writing is still here.', loggedOut: true }, 401);
  if (!env.GITHUB_TOKEN) return json({ error: 'The writing page isn’t connected to GitHub yet (no token saved on the server).' }, 503);

  const form = await request.formData();
  const title = clean(form.get('title'), 90);
  const meal = clean(form.get('meal'), 20);
  const tags = form.getAll('tags').map((t) => slugify(String(t))).filter(Boolean).slice(0, 8);
  const author = clean(form.get('author'), 60);
  const intro = clean(form.get('intro'), 6000);
  const ingredients = lines(clean(form.get('ingredients'), 4000));
  const steps = lines(clean(form.get('steps'), 8000));
  const tips = clean(form.get('tips'), 3000);
  const servings = Number(form.get('servings')) || null;
  const prep = Number(form.get('prep_minutes')) || null;
  const cook = Number(form.get('cook_minutes')) || null;
  const ownPhotos = form.get('own_photos') === 'yes';
  const photoCredit = clean(form.get('photo_credit'), 200);
  const photos = form.getAll('photos').filter((p): p is File => typeof p === 'object' && 'arrayBuffer' in p && p.size > 0);

  const problems: string[] = [];
  if (title.length < 4) problems.push('Add a title.');
  if (!MEALS.includes(meal)) problems.push('Pick a meal.');
  if (ingredients.length < 2) problems.push('Add the ingredients, one per line.');
  if (steps.length < 2) problems.push('Add the steps, one per line.');
  if (!author) problems.push('Add your name for the post.');
  if (photos.length > MAX_PHOTOS) problems.push(`Use ${MAX_PHOTOS} photos or fewer.`);
  if (photos.some((p) => p.size > MAX_PHOTO_BYTES)) problems.push('One of the photos is too big. Try a different one.');
  if (photos.length && !ownPhotos && !photoCredit) problems.push('Say who took the photos, or tick that they’re yours.');
  if (problems.length) return json({ error: problems.join(' '), problems }, 400);

  const date = new Date().toISOString().slice(0, 10);
  const id = `${date}-${slugify(title)}-${crypto.randomUUID().slice(0, 4)}`;
  const dir = `submissions/${id}`;

  const photoFiles = await Promise.all(
    photos.map(async (p, i) => ({ path: `${dir}/photo-${i + 1}.jpg`, base64: toBase64(await p.arrayBuffer()) })),
  );

  const md = [
    '---',
    `title: ${yamlStr(title)}`,
    `author: ${yamlStr(author)}`,
    `submitted: ${date}`,
    `meal: ${meal}`,
    `tags: [${tags.map(yamlStr).join(', ')}]`,
    `servings: ${servings ?? '""'}`,
    `prep_minutes: ${prep ?? '""'}`,
    `cook_minutes: ${cook ?? '""'}`,
    `photos: [${photoFiles.map((f) => yamlStr(f.path.split('/').pop()!)).join(', ')}]`,
    `photo_credit: ${yamlStr(photos.length ? (ownPhotos ? `own photos (${author})` : photoCredit) : '')}`,
    'status: new  # new → priced → published',
    '---',
    '',
    '## About it',
    '',
    intro || '_(no intro written)_',
    '',
    '## Ingredients',
    '',
    ...ingredients.map((l) => `- ${l}`),
    '',
    '## Steps',
    '',
    ...steps.map((l, i) => `${i + 1}. ${l}`),
    '',
    '## Tips',
    '',
    tips || '_(none)_',
    '',
  ].join('\n');

  await commit(env, `Recipe submitted: ${title} (by ${author})`, [
    { path: `${dir}/recipe.md`, text: md },
    ...photoFiles,
  ]);
  return json({ ok: true, id });
}

function toBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let bin = '';
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}

// One commit with every file, via GitHub's Git Data API.
async function commit(env: Env, message: string, files: { path: string; text?: string; base64?: string }[]) {
  const api = `${env.GITHUB_API ?? 'https://api.github.com'}/repos/${env.GITHUB_REPO}`;
  const gh = async (path: string, init: RequestInit = {}) => {
    const res = await fetch(`${api}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: 'application/vnd.github+json',
        'User-Agent': 'gramsperdollar-writer',
        'X-GitHub-Api-Version': '2022-11-28',
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      },
    });
    if (!res.ok) throw new Error(`GitHub ${init.method ?? 'GET'} ${path} → ${res.status} ${await res.text()}`);
    return res.json() as Promise<any>;
  };
  const ref = await gh(`/git/ref/heads/${env.GITHUB_BRANCH}`);
  const parent = await gh(`/git/commits/${ref.object.sha}`);
  const tree = [];
  for (const f of files) {
    const blob = await gh('/git/blobs', {
      method: 'POST',
      body: JSON.stringify(f.base64 != null ? { content: f.base64, encoding: 'base64' } : { content: f.text, encoding: 'utf-8' }),
    });
    tree.push({ path: f.path, mode: '100644', type: 'blob', sha: blob.sha });
  }
  const newTree = await gh('/git/trees', { method: 'POST', body: JSON.stringify({ base_tree: parent.tree.sha, tree }) });
  const c = await gh('/git/commits', { method: 'POST', body: JSON.stringify({ message, tree: newTree.sha, parents: [ref.object.sha] }) });
  await gh(`/git/refs/heads/${env.GITHUB_BRANCH}`, { method: 'PATCH', body: JSON.stringify({ sha: c.sha }) });
}

function json(data: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...headers },
  });
}
