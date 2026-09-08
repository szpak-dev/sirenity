# Testing boundary

Sirenity tests follow **The Fortress Siege & the Meticulous Auntie**:

- Attack only published root API methods, framework endpoints, commands, and installed-package flows.
- Never import `sirenity.*` implementation modules or inspect source files, containers, or internal state.
- Assert observable values, responses, statuses, headers, errors, and caller-visible side effects.
- Give each test one named behavior. Prefer invalid, boundary, and adversarial cases before the happy path.
- Use real application fixtures; use test doubles only for caller-owned public collaborators.
