import { describe, expect, it } from 'vitest';
import { readStartParam, telegramChallengeLink } from './platform';

describe('platform deep-link helpers', () => {
  it('uses Telegram startapp before the plain URL fallback', () => {
    expect(readStartParam('?tgWebAppStartParam=challenge_ABC&startapp=ignored')).toBe('challenge_ABC');
    expect(readStartParam('?startapp=daily')).toBe('daily');
  });

  it('creates an opaque challenge link and fails closed without a username', () => {
    expect(telegramChallengeLink('quiz_battle_bot', 'A B')).toBe('https://t.me/quiz_battle_bot?startapp=challenge_A%20B');
    expect(telegramChallengeLink(undefined, 'ABC')).toBe('');
  });
});
