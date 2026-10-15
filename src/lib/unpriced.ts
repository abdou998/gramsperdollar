// Recipes from /write that aren't priced yet. They get a real recipe page straight away
// (with a "not priced yet" note) so contributors see their work live.
// Once a recipe is priced in data/recipes/<slug>.toml, the priced version takes over the same URL.
import { getCollection } from 'astro:content';
import { allRecipes } from './data';

export type Unpriced = {
  slug: string;
  folder: string;
  title: string;
  author: string;
  date: Date;
  meal: string;
  tags: string[];
  servings: number | null;
  prep: number | null;
  cook: number | null;
  intro: string[];        // paragraphs
  ingredients: string[];
  steps: string[];
  tips: string[];         // paragraphs
  photos: string[];       // file names inside the folder
  photoCredit: string;
};

const slugify = (s: string) =>
  s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').replace(/-recipe$/, '').slice(0, 60);

function section(body: string, name: string): string {
  const m = body.match(new RegExp(`^## ${name}\\s*\\n([\\s\\S]*?)(?=^## |$(?![\\s\\S]))`, 'm'));
  const text = (m?.[1] ?? '').trim();
  return /^_\(.*\)_$/.test(text) ? '' : text;
}
const paragraphs = (t: string) => t.split(/\n\s*\n/).map((p) => p.replace(/\s*\n\s*/g, ' ').trim()).filter(Boolean);
const items = (t: string) => t.split('\n').map((l) => l.replace(/^\s*(?:[-*•]|\d+[.)])\s*/, '').trim()).filter(Boolean);
const n = (v: unknown) => (typeof v === 'number' && v > 0 ? v : null);

let cache: Unpriced[] | undefined;

export async function unpricedRecipes(): Promise<Unpriced[]> {
  if (cache) return cache;
  const taken = new Set(allRecipes().map((r) => r.slug));
  const entries = (await getCollection('submissions', (e) => e.data.status === 'unpriced' || e.data.status === 'new'))
    .sort((a, b) => a.data.submitted.getTime() - b.data.submitted.getTime() || a.id.localeCompare(b.id));
  const out: Unpriced[] = [];
  for (const e of entries) {
    const d = e.data;
    let slug = d.slug ? slugify(d.slug) : slugify(d.title);
    for (let i = 2; taken.has(slug); i++) slug = `${slugify(d.slug ?? d.title)}-${i}`;
    taken.add(slug);
    const body = e.body ?? '';
    out.push({
      slug,
      folder: (e.filePath ?? e.id).replace(/^.*submissions\//, '').split('/')[0],
      title: d.title,
      author: d.author,
      date: d.submitted,
      meal: d.meal,
      tags: d.tags,
      servings: n(d.servings),
      prep: n(d.prep_minutes),
      cook: n(d.cook_minutes),
      intro: paragraphs(section(body, 'About it')),
      ingredients: items(section(body, 'Ingredients')),
      steps: items(section(body, 'Steps')),
      tips: paragraphs(section(body, 'Tips')),
      photos: d.photos,
      photoCredit: d.photo_credit,
    });
  }
  return (cache = out.reverse()); // newest first
}

// Photos live next to each recipe.md in submissions/. Vite picks them up here for optimisation.
const photoFiles = import.meta.glob<{ default: ImageMetadata }>('/submissions/*/*.{jpg,jpeg,png,webp}', { eager: true });
export function photoFor(u: Unpriced, i = 0): ImageMetadata | undefined {
  const name = u.photos[i];
  return name ? photoFiles[`/submissions/${u.folder}/${name}`]?.default : undefined;
}
