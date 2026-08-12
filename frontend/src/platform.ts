/** Platform-neutral helpers that can be tested outside Telegram/MAX clients. */
export function readStartParam(search: string): string {
  const values = new URLSearchParams(search);
  return values.get('tgWebAppStartParam') || values.get('startapp') || '';
}

export function telegramChallengeLink(username: string | undefined, code: string): string {
  if (!username || !code) return '';
  return `https://t.me/${username}?startapp=challenge_${encodeURIComponent(code)}`;
}

export type AchievementDetails = {icon:string;title:string;description:string};

const ACHIEVEMENTS:Record<string,AchievementDetails> = {
  first_game:{icon:'🎮',title:'Первый раунд',description:'Заверши свою первую игру.'},
  perfect:{icon:'💎',title:'Идеальный раунд',description:'Ответь верно на все вопросы.'},
  streak_3:{icon:'🔥',title:'Серия: 3 дня',description:'Играй в квиз дня три дня подряд.'},
  streak_7:{icon:'⚡',title:'Серия: 7 дней',description:'Играй в квиз дня семь дней подряд.'},
};

export function achievementDetails(code:string):AchievementDetails {
  return ACHIEVEMENTS[code] || {icon:'🏅',title:code.replace(/_/g,' '),description:'Получено в Quiz Battle.'};
}
