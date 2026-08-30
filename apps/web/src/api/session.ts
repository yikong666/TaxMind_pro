let accessToken: string | null = null;

export function setAccessToken(value: string): void {
  accessToken = value;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function clearAccessToken(): void {
  accessToken = null;
}
