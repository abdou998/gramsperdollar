// Recipe photos live in src/assets/images; recipes name theirs in `image`.
const images = import.meta.glob<{ default: ImageMetadata }>('../assets/images/*.{jpg,jpeg,png,webp}', { eager: true });
export function recipeImage(file?: string | null): ImageMetadata | undefined {
  return file ? images[`../assets/images/${file}`]?.default : undefined;
}
