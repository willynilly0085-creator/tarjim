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

## Problèmes connus dans les bibliothèques

Des vulnérabilités publiées dans des bibliothèques installées par tarjim, qu'aucune version testée ne peut encore éviter, car qwen-asr (le moteur d'écoute local) exige exactement transformers 4.57.6 et cesse de fonctionner avec toute version 5. La façon dont tarjim utilise la bibliothèque n'en atteint aucune : chaque modèle de Hugging Face est téléchargé depuis une version fixe vérifiée par tarjim, avec seulement ses fichiers de réglages et de poids (jamais de code), et chargé depuis son dossier sur l'ordinateur, hors ligne. Les réglages montrent celles qui concernent votre ordinateur, et chacune disparaît d'elle-même quand une mise à jour installe une version corrigée.

| Avis | Bibliothèque | Versions touchées | Corrigé dans |
|---|---|---|---|
| PYSEC-2025-217 | transformers | `<=5.0.0rc0` | 5.0.0 |
| PYSEC-2026-2288 | transformers | `<5.0.0` | 5.0.0 |
| PYSEC-2026-2289 | transformers | `<5.3.0` | 5.3.0 |
| PYSEC-2026-2290 | transformers | `<5.5.0` | 5.5.0 |
| PYSEC-2026-3929 | transformers | `<5.10.0` | 5.10.0 |
| PYSEC-2026-4174 | transformers | `>=4.49.0,<=5.8.1` | 5.9.0 |

Détails (en anglais) : [SECURITY.md](../../SECURITY.md#known-library-issues).
