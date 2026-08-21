const apiVersion = import.meta.env.VITE_API_VERSION;

export function getApiUrl(endpoint: string): string {
  if (!apiVersion) {
    throw new Error('API version is not defined in environment variables.');
  }
  return `/api/${apiVersion}/${endpoint}`;
}

// Example usage:
// const url = getApiUrl('users');