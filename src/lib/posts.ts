import { getCollection } from 'astro:content';

export async function publishedPosts() {
  return (await getCollection('posts', ({ data }) => !data.draft))
    .sort((a, b) => b.data.published.valueOf() - a.data.published.valueOf());
}

/** Posts that feature a recipe (via the `recipes` frontmatter list). */
export async function postsFeaturing(slug: string) {
  return (await publishedPosts()).filter((p) => p.data.recipes.includes(slug));
}
