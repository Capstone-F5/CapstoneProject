export function normalizeSetOptions(options = []) {
  const available = options.filter(option => option.is_available !== false)
  const asChoice = option => ({
    name: option.name_ko,
    nameEn: option.name_en,
    extra: Number(option.additional_price ?? 0),
  })

  return {
    setSides: available
      .filter(option => option.option_group === 'SET_SIDE')
      .map(asChoice),
    setDrinks: available
      .filter(option => option.option_group === 'SET_DRINK')
      .map(asChoice),
    setSurcharge: Number(
      available.find(option => option.option_group === 'SET_UPGRADE')?.additional_price ?? 0
    ),
  }
}

export function findMenuOption(menu, group, name) {
  return menu?.options?.find(option =>
    option.is_available !== false &&
    option.option_group === group &&
    (name == null || option.name_ko === name || option.name_en === name)
  )
}
