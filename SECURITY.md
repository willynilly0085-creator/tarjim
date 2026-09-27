# Security

## Reporting a problem

Please report security problems privately through GitHub's "Report a vulnerability" button on this
repository, not in a public issue. Describe what you found, how to reproduce it, and what it lets
someone do. Reports are read and answered as soon as possible.

## What tarjim protects

- **Keys and the pairing token** live in the operating system's encrypted vault through `keyring`.
  They never appear in the settings file, in server responses, in logs or in chat tools.
- **The local server** (`tarjim-serve`) listens on 127.0.0.1 only and refuses:
  - requests without the token (`X-Tarjim-Token`) or the page's HttpOnly, SameSite=Strict cookie;
  - requests whose `Host` is not local (DNS rebinding);
  - pairing requests that do not come from a browser extension;
  - any path outside its own web folder and the finished outputs of a job.
- **Subscriptions** are used by running the vendor's own program (Claude Code, Codex, Copilot,
  Antigravity). tarjim never reads or stores their sign-in files or tokens.
- **Local mode** keeps media on the device: models load with the Hugging Face hub offline, and the
  network is used only while downloading a tool the person asked for.
- **Downloads**: ffmpeg is checked against the SHA-256 published with its release.

## Known limits

- Anyone who can run programs as your user on your computer can read the vault and the token.
  tarjim does not defend against a compromised account.
- Cloud providers you choose receive the audio or text they process, under their own terms.
