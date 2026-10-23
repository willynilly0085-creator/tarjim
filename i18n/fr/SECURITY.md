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

Vulnérabilités publiées dans les bibliothèques installées par tarjim qu'aucune version testée ne peut encore éviter : aucune pour l'instant. Si une apparaît, ses informations arrivent avec tarjim dans `tarjim/known_issues.json` : **Réglages**, la réponse `/update` du moteur et `setup_status` des outils de chat l'affichent sur les ordinateurs dont la version installée est concernée, et elle disparaît d'elle-même dès qu'une mise à jour installe une version corrigée. La CI échoue pour toute vulnérabilité absente de cette liste, et une vérification hebdomadaire signale quand une vulnérabilité listée peut être corrigée.

**Fermées le 2026-10-23.** Six avis transformers (PYSEC-2025-217, PYSEC-2026-2288, PYSEC-2026-2289, PYSEC-2026-2290, PYSEC-2026-3929, PYSEC-2026-4174) sont restés ouverts tant que qwen-asr, le moteur d'écoute local de l'époque, bloquait transformers en 4.57.6. L'écoute locale utilise désormais les modèles Qwen3-ASR propres à Transformers : tarjim installe transformers 5.20.2 et n'installe plus qwen-asr ; accelerate reste en 1.15.0 (PYSEC-2026-3804 fermée) sans aucune dérogation.

**Ce que tarjim fait dans tous les cas.** Chaque modèle Hugging Face est téléchargé depuis un commit fixe (`tarjim/model_pins.py`), uniquement ses réglages, son tokenizer, son modèle de chat et ses fichiers safetensors, jamais de code ; ses gros fichiers doivent correspondre à leur SHA-256 publié, et il est chargé depuis ce dossier sur l'ordinateur, hub hors ligne. `trust_remote_code` n'est jamais activé et le paquet `kernels` n'est pas installé. Les poids de séparation des voix ne se chargent que s'ils nomment la classe de modèle de demucs, et le modèle de diacritiques que si ses deux fichiers correspondent au SHA-256 de leur version.
