import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

// Posts live in src/content/posts as .md or .mdx. The file name becomes the URL:
// src/content/posts/high-protein-meal-prep-for-one.mdx -> /high-protein-meal-prep-for-one
// Files starting with _ are ignored (drafts/templates).
const posts = defineCollection({
  loader: glob({ pattern: '**/[^_]*.{md,mdx}', base: './src/content/posts' }),
  schema: ({ image }) =>
    z.object({
      title: z.string().max(70),            // Google shows ~60 characters
      description: z.string().max(160),     // the snippet under the title
      published: z.coerce.date(),
      updated: z.coerce.date().optional(),
      author: z.string().default('Grams per Dollar'),
      hero: image().optional(),
      heroAlt: z.string().optional(),
      heroCredit: z.string().optional(),
      recipes: z.array(z.string()).default([]), // recipe slugs this post features (links them both ways)
      listRecipesAtEnd: z.boolean().default(true), // set false if the post places <RecipeList> itself (.mdx)
      draft: z.boolean().default(false),
    }),
});

// Recipes sent from /write. They go live straight away as "not priced yet" recipe pages,
// until they're priced in data/recipes/ (then set status: priced and the priced page takes over the URL).
const submissions = defineCollection({
  loader: glob({ pattern: '*/recipe.md', base: './submissions' }),
  schema: z.object({
    title: z.string(),
    slug: z.string().optional(),
    author: z.string(),
    submitted: z.coerce.date(),
    meal: z.enum(['breakfast', 'lunch', 'dinner', 'snack']),
    tags: z.array(z.string()).default([]),
    servings: z.union([z.number(), z.literal('')]).optional(),
    prep_minutes: z.union([z.number(), z.literal('')]).optional(),
    cook_minutes: z.union([z.number(), z.literal('')]).optional(),
    photos: z.array(z.string()).default([]),
    photo_credit: z.string().default(''),
    status: z.enum(['new', 'unpriced', 'priced', 'hidden']).default('unpriced'),
  }),
});

export const collections = { posts, submissions };
