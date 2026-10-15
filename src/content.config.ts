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
      recipes: z.array(z.string()).default([]), // recipe slugs shown at the end (for plain .md posts)
      draft: z.boolean().default(false),
    }),
});

export const collections = { posts };
