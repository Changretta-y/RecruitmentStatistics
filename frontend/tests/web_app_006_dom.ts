// Public labels, groups, and controls of a mounted form; no production internals.
export function publicControl(wrapper: any, text: string) {
  const direct = wrapper.find(`[aria-label="${text}"]`);
  if (direct.exists()) return direct;
  const label = wrapper.findAll('label').find((candidate: any) => candidate.text().replace(/\*/g, '').trim() === text);
  if (!label) throw new Error(`Missing public label: ${text}`);
  const id = label.attributes('for');
  return id ? wrapper.get(`[id="${id}"]`) : label.get('input, select, textarea');
}
export function publicGroup(wrapper: any, text: string) {
  const group = wrapper.findAll('fieldset, [role="group"]').find((candidate: any) => {
    const legend = candidate.find('legend');
    return candidate.attributes('aria-label') === text || (legend.exists() && legend.text().trim() === text);
  });
  if (!group) throw new Error(`Missing public group: ${text}`);
  return group;
}
export function publicButton(wrapper: any, text: string) {
  const button = wrapper.findAll('button').find((candidate: any) => candidate.text().trim() === text || candidate.attributes('aria-label') === text);
  if (!button) throw new Error(`Missing public button: ${text}`);
  return button;
}
