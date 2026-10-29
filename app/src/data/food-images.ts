// Keyword → photo in public/img. Generated ingredient ids/names vary, so match on substrings.
const PHOTOS: [RegExp, string][] = [
  [/spinach|greens|kale/i, 'spinach'],
  [/grilled/i, 'grilled'],
  [/chicken|turkey/i, 'chicken'],
  [/pepper/i, 'peppers'],
  [/yogurt|parfait/i, 'yogurt'],
  [/quinoa/i, 'quinoa'],
  [/rice/i, 'rice'],
  [/cheddar|cheese|mac/i, 'cheddar'],
  [/tomato/i, 'tomatoes'],
  [/milk/i, 'milk'],
  [/banana/i, 'bananas'],
  [/roast|vegetable/i, 'roasted'],
  [/roll|bread|bun|bagel/i, 'roll'],
]

export function foodPhoto(...keys: (string | undefined)[]): string | null {
  const hay = keys.filter(Boolean).join(' ')
  const hit = PHOTOS.find(([re]) => re.test(hay))
  return hit ? `${import.meta.env.BASE_URL}img/${hit[1]}.jpg` : null
}
