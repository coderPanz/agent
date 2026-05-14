---
name: feedback_commit_push
description: 用户提交代码时，默认同时执行 push
metadata:
  type: feedback
---

「提交代码」= commit + push，两步一起执行。

**Why:** 用户明确表示希望提交时顺便推送到远端，不需要单独再说 push。

**How to apply:** 每当用户说「提交代码」「提交」「commit」时，在 git commit 成功后立即执行 `git push`，无需再次确认。
