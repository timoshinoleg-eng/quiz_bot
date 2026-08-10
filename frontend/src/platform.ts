/** Platform-neutral helpers that can be tested outside Telegram/MAX clients. */
export function readStartParam(search: string): string {
  const values = new URLSearchParams(search);
  return values.get('tgWebAppStartParam') || values.get('startapp') || '';
}

export function telegramChallengeLink(username: string | undefined, code: string): string {
  if (!username || !code) return '';
  return `https://t.me/${username}?startapp=challenge_${encodeURIComponent(code)}`;
}
