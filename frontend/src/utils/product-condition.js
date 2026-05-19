export const PRODUCT_CONDITION_OPTIONS = ['New', 'Like New', 'Good', 'Fair', 'Poor']

const conditionLabelByKey = PRODUCT_CONDITION_OPTIONS.reduce((labels, condition) => {
  labels[condition.toLowerCase()] = condition
  return labels
}, {})

export const normalizeProductCondition = (value) => {
  const label = String(value ?? '').trim()

  if (!label) {
    return ''
  }

  return conditionLabelByKey[label.toLowerCase()] || label
}

export const getProductCondition = (product) =>
  normalizeProductCondition(product?.condition) || 'Unspecified'

export const getConditionBadgeClass = (condition) => {
  const normalizedCondition = normalizeProductCondition(condition).toLowerCase().replace(/\s+/g, '-')

  return {
    'condition-badge--new': normalizedCondition === 'new',
    'condition-badge--like-new': normalizedCondition === 'like-new',
    'condition-badge--good': normalizedCondition === 'good',
    'condition-badge--fair': normalizedCondition === 'fair',
    'condition-badge--poor': normalizedCondition === 'poor',
  }
}
