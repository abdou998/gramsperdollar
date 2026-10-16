// Shared bits of schema.org Recipe markup.

/** Each step as a HowToStep with a short `name` (Google suggests one). Uses the text before a colon
 *  ("Make the base: …") if there is one, otherwise the first sentence, trimmed to a few words. */
export function howToSteps(steps: string[]) {
  return steps.map((text, i) => {
    const lead = text.match(/^([^:.!?]{3,60}):\s/)?.[1] ?? text.split(/(?<=[.!?])\s/)[0];
    const words = lead.replace(/[.!?]$/, '').split(/\s+/);
    const name = words.length > 8 ? `${words.slice(0, 8).join(' ')}…` : words.join(' ');
    return { '@type': 'HowToStep', position: i + 1, name, text };
  });
}

export const SITE_AUTHOR = { '@type': 'Organization', name: 'Grams per Dollar', url: 'https://gramsperdollar.com/about' };
