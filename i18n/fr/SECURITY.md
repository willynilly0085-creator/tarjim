# Sécurité
<!-- languages -->
[English](../../SECURITY.md) · [العربية](../../i18n/ar/SECURITY.md) · [Español](../../i18n/es/SECURITY.md) · **Français** · [Português](../../i18n/pt/SECURITY.md) · [Deutsch](../../i18n/de/SECURITY.md) · [Русский](../../i18n/ru/SECURITY.md) · [Türkçe](../../i18n/tr/SECURITY.md) · [हिन्दी](../../i18n/hi/SECURITY.md) · [اردو](../../i18n/ur/SECURITY.md) · [Bahasa Indonesia](../../i18n/id/SECURITY.md) · [日本語](../../i18n/ja/SECURITY.md) · [中文](../../i18n/zh/SECURITY.md) · [한국어](../../i18n/ko/SECURITY.md)

## Signaler un problème

Merci de signaler les problèmes de sécurité en privé via le bouton **Report a vulnerability**
(signaler une vulnérabilité) de GitHub sur ce dépôt, et non dans une issue publique. Décrivez ce que
vous avez trouvé, comment le reproduire et ce que cela permet de faire. Les signalements sont lus
et traités dans les meilleurs délais.

## Ce que tarjim protège

- **Les clés et le jeton d'appairage** sont conservés dans le coffre chiffré du système
  d'exploitation via `keyring`. Ils n'apparaissent jamais dans le fichier de réglages, dans les
  réponses du serveur, dans les journaux ni dans les outils de conversation.
- **Le serveur local** (`tarjim-serve`) n'écoute que sur 127.0.0.1 et refuse :
  - les requêtes sans le jeton (`X-Tarjim-Token`) ni le cookie HttpOnly, SameSite=Strict de la page ;
  - les requêtes dont le `Host` n'est pas local (DNS rebinding) ;
  - les demandes d'appairage qui ne proviennent pas d'une extension de navigateur ;
  - tout chemin situé hors de son propre dossier web et des résultats terminés d'une tâche.
- **Les abonnements** sont utilisés en lançant le programme du fournisseur lui-même (Claude Code,
  Codex, Copilot, Antigravity). tarjim ne lit ni ne stocke jamais leurs fichiers de connexion ou
  leurs jetons.
- **Le mode local** garde les médias sur l'appareil : les modèles se chargent avec le hub Hugging
  Face hors ligne, et le réseau n'est utilisé que pendant le téléchargement d'un outil demandé par
  la personne.
- **Téléchargements** : ffmpeg est vérifié à l'aide de l'empreinte SHA-256 publiée avec sa version.

## Limites connues

- Toute personne capable d'exécuter des programmes sous votre compte utilisateur sur votre
  ordinateur peut lire le coffre et le jeton. tarjim ne protège pas contre un compte compromis.
- Les fournisseurs cloud que vous choisissez reçoivent l'audio ou le texte qu'ils traitent, selon
  leurs propres conditions.
