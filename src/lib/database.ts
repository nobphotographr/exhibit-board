// Disabled for demo deployment - original file backed up
export const DatabaseService = {
  getEvents: async () => [],
  createEvent: async () => ({ id: 'demo' }),
  checkDuplicateUrl: async () => false
}

export const EventValidator = {
  validateUrl: () => true,
  validateDateRange: () => true,
  validateRequiredFields: () => [],
  validateEvent: () => ({ valid: true, errors: [] })
}