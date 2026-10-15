var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// worker/index.ts
var COOKIE = "gpd_writer";
var SESSION_DAYS = 30;
var MAX_PHOTOS = 6;
var MAX_PHOTO_BYTES = 4 * 1024 * 1024;
var MEALS = ["breakfast", "lunch", "dinner", "snack"];
var worker_default = {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/api/")) return env.ASSETS.fetch(request);
    try {
      if (url.pathname === "/api/session" && request.method === "GET") return session(request, env);
      if (url.pathname === "/api/login" && request.method === "POST") return login(request, env);
      if (url.pathname === "/api/logout" && request.method === "POST") return logout();
      if (url.pathname === "/api/submit" && request.method === "POST") return submit(request, env);
      return json({ error: "Not found." }, 404);
    } catch (e) {
      console.error(e);
      return json({ error: "Something went wrong on our side. Your writing is still saved on this device. Try again in a minute." }, 500);
    }
  }
};
async function hmac(key, msg) {
  const k = await crypto.subtle.importKey("raw", new TextEncoder().encode(key), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", k, new TextEncoder().encode(msg));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
__name(hmac, "hmac");
async function sameText(a, b) {
  const [x, y] = await Promise.all([hmac("cmp", a), hmac("cmp", b)]);
  return x === y;
}
__name(sameText, "sameText");
async function makeToken(env) {
  const exp = Date.now() + SESSION_DAYS * 864e5;
  return `${exp}.${await hmac(env.WRITER_PASSWORD, String(exp))}`;
}
__name(makeToken, "makeToken");
async function loggedIn(request, env) {
  if (!env.WRITER_PASSWORD) return false;
  const raw = (request.headers.get("Cookie") ?? "").split(/;\s*/).find((c) => c.startsWith(`${COOKIE}=`));
  if (!raw) return false;
  const [exp, sig] = raw.slice(COOKIE.length + 1).split(".");
  if (!exp || !sig || Number(exp) < Date.now()) return false;
  return sameText(sig, await hmac(env.WRITER_PASSWORD, exp));
}
__name(loggedIn, "loggedIn");
var cookie = /* @__PURE__ */ __name((value, maxAge) => `${COOKIE}=${value}; Path=/api; HttpOnly; Secure; SameSite=Strict; Max-Age=${maxAge}`, "cookie");
async function session(request, env) {
  return json({ loggedIn: await loggedIn(request, env), configured: Boolean(env.WRITER_PASSWORD && env.GITHUB_TOKEN) });
}
__name(session, "session");
async function login(request, env) {
  if (!env.WRITER_PASSWORD) return json({ error: "The writing page isn\u2019t set up yet (no password saved on the server)." }, 503);
  const { password } = await request.json().catch(() => ({}));
  await new Promise((r) => setTimeout(r, 400));
  if (!password || !await sameText(password, env.WRITER_PASSWORD)) return json({ error: "That password didn\u2019t work. Check it and try again." }, 401);
  return json({ ok: true }, 200, { "Set-Cookie": cookie(await makeToken(env), SESSION_DAYS * 86400) });
}
__name(login, "login");
function logout() {
  return json({ ok: true }, 200, { "Set-Cookie": cookie("", 0) });
}
__name(logout, "logout");
var clean = /* @__PURE__ */ __name((v, max = 5e3) => String(v ?? "").replace(/\r\n/g, "\n").trim().slice(0, max), "clean");
var lines = /* @__PURE__ */ __name((s) => s.split("\n").map((l) => l.replace(/^\s*(?:[-*•]|\d+[.)])\s*/, "").trim()).filter(Boolean), "lines");
var slugify = /* @__PURE__ */ __name((s) => s.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/&/g, " and ").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "recipe", "slugify");
var yamlStr = /* @__PURE__ */ __name((s) => JSON.stringify(s), "yamlStr");
async function submit(request, env) {
  if (!await loggedIn(request, env)) return json({ error: "You\u2019ve been logged out. Log in again; your writing is still here.", loggedOut: true }, 401);
  if (!env.GITHUB_TOKEN) return json({ error: "The writing page isn\u2019t connected to GitHub yet (no token saved on the server)." }, 503);
  const form = await request.formData();
  const title = clean(form.get("title"), 90);
  const meal = clean(form.get("meal"), 20);
  const tags = form.getAll("tags").map((t) => slugify(String(t))).filter(Boolean).slice(0, 8);
  const author = clean(form.get("author"), 60);
  const intro = clean(form.get("intro"), 6e3);
  const ingredients = lines(clean(form.get("ingredients"), 4e3));
  const steps = lines(clean(form.get("steps"), 8e3));
  const tips = clean(form.get("tips"), 3e3);
  const servings = Number(form.get("servings")) || null;
  const prep = Number(form.get("prep_minutes")) || null;
  const cook = Number(form.get("cook_minutes")) || null;
  const ownPhotos = form.get("own_photos") === "yes";
  const photoCredit = clean(form.get("photo_credit"), 200);
  const photos = form.getAll("photos").filter((p) => typeof p === "object" && "arrayBuffer" in p && p.size > 0);
  const problems = [];
  if (title.length < 4) problems.push("Add a title.");
  if (!MEALS.includes(meal)) problems.push("Pick a meal.");
  if (ingredients.length < 2) problems.push("Add the ingredients, one per line.");
  if (steps.length < 2) problems.push("Add the steps, one per line.");
  if (!author) problems.push("Add your name for the post.");
  if (photos.length > MAX_PHOTOS) problems.push(`Use ${MAX_PHOTOS} photos or fewer.`);
  if (photos.some((p) => p.size > MAX_PHOTO_BYTES)) problems.push("One of the photos is too big. Try a different one.");
  if (photos.length && !ownPhotos && !photoCredit) problems.push("Say who took the photos, or tick that they\u2019re yours.");
  if (problems.length) return json({ error: problems.join(" "), problems }, 400);
  const date = (/* @__PURE__ */ new Date()).toISOString().slice(0, 10);
  const id = `${date}-${slugify(title)}-${crypto.randomUUID().slice(0, 4)}`;
  const dir = `submissions/${id}`;
  const photoFiles = await Promise.all(
    photos.map(async (p, i) => ({ path: `${dir}/photo-${i + 1}.jpg`, base64: toBase64(await p.arrayBuffer()) }))
  );
  const md = [
    "---",
    `title: ${yamlStr(title)}`,
    `author: ${yamlStr(author)}`,
    `submitted: ${date}`,
    `meal: ${meal}`,
    `tags: [${tags.map(yamlStr).join(", ")}]`,
    `servings: ${servings ?? '""'}`,
    `prep_minutes: ${prep ?? '""'}`,
    `cook_minutes: ${cook ?? '""'}`,
    `photos: [${photoFiles.map((f) => yamlStr(f.path.split("/").pop())).join(", ")}]`,
    `photo_credit: ${yamlStr(photos.length ? ownPhotos ? `own photos (${author})` : photoCredit : "")}`,
    "status: new  # new \u2192 priced \u2192 published",
    "---",
    "",
    "## About it",
    "",
    intro || "_(no intro written)_",
    "",
    "## Ingredients",
    "",
    ...ingredients.map((l) => `- ${l}`),
    "",
    "## Steps",
    "",
    ...steps.map((l, i) => `${i + 1}. ${l}`),
    "",
    "## Tips",
    "",
    tips || "_(none)_",
    ""
  ].join("\n");
  await commit(env, `Recipe submitted: ${title} (by ${author})`, [
    { path: `${dir}/recipe.md`, text: md },
    ...photoFiles
  ]);
  return json({ ok: true, id });
}
__name(submit, "submit");
function toBase64(buf) {
  const bytes = new Uint8Array(buf);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 32768) bin += String.fromCharCode(...bytes.subarray(i, i + 32768));
  return btoa(bin);
}
__name(toBase64, "toBase64");
async function commit(env, message, files) {
  const api = `${env.GITHUB_API ?? "https://api.github.com"}/repos/${env.GITHUB_REPO}`;
  const gh = /* @__PURE__ */ __name(async (path, init = {}) => {
    const res = await fetch(`${api}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "gramsperdollar-writer",
        "X-GitHub-Api-Version": "2022-11-28",
        ...init.body ? { "Content-Type": "application/json" } : {}
      }
    });
    if (!res.ok) throw new Error(`GitHub ${init.method ?? "GET"} ${path} \u2192 ${res.status} ${await res.text()}`);
    return res.json();
  }, "gh");
  const ref = await gh(`/git/ref/heads/${env.GITHUB_BRANCH}`);
  const parent = await gh(`/git/commits/${ref.object.sha}`);
  const tree = [];
  for (const f of files) {
    const blob = await gh("/git/blobs", {
      method: "POST",
      body: JSON.stringify(f.base64 != null ? { content: f.base64, encoding: "base64" } : { content: f.text, encoding: "utf-8" })
    });
    tree.push({ path: f.path, mode: "100644", type: "blob", sha: blob.sha });
  }
  const newTree = await gh("/git/trees", { method: "POST", body: JSON.stringify({ base_tree: parent.tree.sha, tree }) });
  const c = await gh("/git/commits", { method: "POST", body: JSON.stringify({ message, tree: newTree.sha, parents: [ref.object.sha] }) });
  await gh(`/git/refs/heads/${env.GITHUB_BRANCH}`, { method: "PATCH", body: JSON.stringify({ sha: c.sha }) });
}
__name(commit, "commit");
function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...headers }
  });
}
__name(json, "json");

// ../.npm/_npx/32026684e21afda6/node_modules/wrangler/templates/middleware/middleware-ensure-req-body-drained.ts
var drainBody = /* @__PURE__ */ __name(async (request, env, _ctx, middlewareCtx) => {
  try {
    return await middlewareCtx.next(request, env);
  } finally {
    try {
      if (request.body !== null && !request.bodyUsed) {
        const reader = request.body.getReader();
        while (!(await reader.read()).done) {
        }
      }
    } catch (e) {
      console.error("Failed to drain the unused request body.", e);
    }
  }
}, "drainBody");
var middleware_ensure_req_body_drained_default = drainBody;

// ../.npm/_npx/32026684e21afda6/node_modules/wrangler/templates/middleware/middleware-miniflare3-json-error.ts
function reduceError(e) {
  return {
    name: e?.name,
    message: e?.message ?? String(e),
    stack: e?.stack,
    cause: e?.cause === void 0 ? void 0 : reduceError(e.cause)
  };
}
__name(reduceError, "reduceError");
var jsonError = /* @__PURE__ */ __name(async (request, env, _ctx, middlewareCtx) => {
  try {
    return await middlewareCtx.next(request, env);
  } catch (e) {
    const error = reduceError(e);
    const body = JSON.stringify(error);
    const headers = {
      "Content-Type": "application/json",
      "MF-Experimental-Error-Stack": "true"
    };
    const encoded = encodeURIComponent(body);
    if (encoded.length <= 8192) {
      headers["MF-Experimental-Error-Stack-Payload"] = encoded;
    }
    return new Response(body, { status: 500, headers });
  }
}, "jsonError");
var middleware_miniflare3_json_error_default = jsonError;

// .wrangler/tmp/bundle-244ihm/middleware-insertion-facade.js
var __INTERNAL_WRANGLER_MIDDLEWARE__ = [
  middleware_ensure_req_body_drained_default,
  middleware_miniflare3_json_error_default
];
var middleware_insertion_facade_default = worker_default;

// ../.npm/_npx/32026684e21afda6/node_modules/wrangler/templates/middleware/common.ts
var __facade_middleware__ = [];
function __facade_register__(...args) {
  __facade_middleware__.push(...args.flat());
}
__name(__facade_register__, "__facade_register__");
function __facade_invokeChain__(request, env, ctx, dispatch, middlewareChain) {
  const [head, ...tail] = middlewareChain;
  const middlewareCtx = {
    dispatch,
    next(newRequest, newEnv) {
      return __facade_invokeChain__(newRequest, newEnv, ctx, dispatch, tail);
    }
  };
  return head(request, env, ctx, middlewareCtx);
}
__name(__facade_invokeChain__, "__facade_invokeChain__");
function __facade_invoke__(request, env, ctx, dispatch, finalMiddleware) {
  return __facade_invokeChain__(request, env, ctx, dispatch, [
    ...__facade_middleware__,
    finalMiddleware
  ]);
}
__name(__facade_invoke__, "__facade_invoke__");

// .wrangler/tmp/bundle-244ihm/middleware-loader.entry.ts
var __Facade_ScheduledController__ = class ___Facade_ScheduledController__ {
  constructor(scheduledTime, cron, noRetry) {
    this.scheduledTime = scheduledTime;
    this.cron = cron;
    this.#noRetry = noRetry;
  }
  scheduledTime;
  cron;
  static {
    __name(this, "__Facade_ScheduledController__");
  }
  #noRetry;
  noRetry() {
    if (!(this instanceof ___Facade_ScheduledController__)) {
      throw new TypeError("Illegal invocation");
    }
    this.#noRetry();
  }
};
function wrapExportedHandler(worker) {
  if (__INTERNAL_WRANGLER_MIDDLEWARE__ === void 0 || __INTERNAL_WRANGLER_MIDDLEWARE__.length === 0) {
    return worker;
  }
  for (const middleware of __INTERNAL_WRANGLER_MIDDLEWARE__) {
    __facade_register__(middleware);
  }
  const fetchDispatcher = /* @__PURE__ */ __name(function(request, env, ctx) {
    if (worker.fetch === void 0) {
      throw new Error("Handler does not export a fetch() function.");
    }
    return worker.fetch(request, env, ctx);
  }, "fetchDispatcher");
  return {
    ...worker,
    fetch(request, env, ctx) {
      const dispatcher = /* @__PURE__ */ __name(function(type, init) {
        if (type === "scheduled" && worker.scheduled !== void 0) {
          const controller = new __Facade_ScheduledController__(
            Date.now(),
            init.cron ?? "",
            () => {
            }
          );
          return worker.scheduled(controller, env, ctx);
        }
      }, "dispatcher");
      return __facade_invoke__(request, env, ctx, dispatcher, fetchDispatcher);
    }
  };
}
__name(wrapExportedHandler, "wrapExportedHandler");
function wrapWorkerEntrypoint(klass) {
  if (__INTERNAL_WRANGLER_MIDDLEWARE__ === void 0 || __INTERNAL_WRANGLER_MIDDLEWARE__.length === 0) {
    return klass;
  }
  for (const middleware of __INTERNAL_WRANGLER_MIDDLEWARE__) {
    __facade_register__(middleware);
  }
  return class extends klass {
    #fetchDispatcher = /* @__PURE__ */ __name((request, env, ctx) => {
      this.env = env;
      this.ctx = ctx;
      if (super.fetch === void 0) {
        throw new Error("Entrypoint class does not define a fetch() function.");
      }
      return super.fetch(request);
    }, "#fetchDispatcher");
    #dispatcher = /* @__PURE__ */ __name((type, init) => {
      if (type === "scheduled" && super.scheduled !== void 0) {
        const controller = new __Facade_ScheduledController__(
          Date.now(),
          init.cron ?? "",
          () => {
          }
        );
        return super.scheduled(controller);
      }
    }, "#dispatcher");
    fetch(request) {
      return __facade_invoke__(
        request,
        this.env,
        this.ctx,
        this.#dispatcher,
        this.#fetchDispatcher
      );
    }
  };
}
__name(wrapWorkerEntrypoint, "wrapWorkerEntrypoint");
var WRAPPED_ENTRY;
if (typeof middleware_insertion_facade_default === "object") {
  WRAPPED_ENTRY = wrapExportedHandler(middleware_insertion_facade_default);
} else if (typeof middleware_insertion_facade_default === "function") {
  WRAPPED_ENTRY = wrapWorkerEntrypoint(middleware_insertion_facade_default);
}
var middleware_loader_entry_default = WRAPPED_ENTRY;
export {
  __INTERNAL_WRANGLER_MIDDLEWARE__,
  middleware_loader_entry_default as default
};
//# sourceMappingURL=index.js.map
