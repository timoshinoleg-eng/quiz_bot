# V2 references

MAX official documentation checked on 2026-08-10: [MAX Bridge](https://dev.max.ru/docs/webapps/bridge), [initData validation](https://dev.max.ru/docs/webapps/validation), and [Mini App connection](https://dev.max.ru/docs/webapps/introduction). The implementation uses `window.WebApp`, signed `initData`, server HMAC validation, BackButton and haptic/share fallbacks. MAX requires a bot-linked HTTPS application; a Partner Cabinet registration remains an owner-side deployment gate.

OpenTDB, The Trivia API and QuizAPI are deliberately outside gameplay runtime. Licensing must be rechecked immediately before any provider import.
