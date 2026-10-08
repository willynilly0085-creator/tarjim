# tarjim
<!-- languages -->
[English](../../README.md) · [العربية](../../i18n/ar/README.md) · [Español](../../i18n/es/README.md) · **Français** · [Português](../../i18n/pt/README.md) · [Deutsch](../../i18n/de/README.md) · [Русский](../../i18n/ru/README.md) · [Türkçe](../../i18n/tr/README.md) · [हिन्दी](../../i18n/hi/README.md) · [اردو](../../i18n/ur/README.md) · [Bahasa Indonesia](../../i18n/id/README.md) · [日本語](../../i18n/ja/README.md) · [中文](../../i18n/zh/README.md) · [한국어](../../i18n/ko/README.md)

Développé par [Indicators](https://indicators.sa/) · [indicators.sa](https://indicators.sa/)

**Sous-titres et doublage pour n'importe quelle vidéo, dans votre langue, sur votre propre ordinateur.**

Collez un lien ou déposez un fichier. tarjim écoute, cale chaque réplique sur l'instant exact où
elle est prononcée, distingue chaque locuteur, traduit dans une langue naturelle, puis incruste les
sous-titres dans la vidéo, produit un fichier `.srt` ou la double avec une voix pour chaque locuteur.

## Ce qu'il fait

- **N'importe quelle source :** liens YouTube, X et autres (yt-dlp), ou tout fichier vidéo ou audio présent sur votre appareil.
- **34 langues cibles**, de droite à gauche comme de gauche à droite. L'arabe utilise par défaut un
  dialecte saoudien ; l'arabe standard moderne est à un clic.
- **Écoute attentive :** l'audio est écouté trois fois et chaque mot est soumis à un vote, si bien
  qu'une erreur d'écoute isolée n'atteint jamais le sous-titre.
- **Synchronisation exacte :** les mots sont alignés sur l'audio sur votre ordinateur (alignement
  forcé CTC et détection d'activité vocale). Un sous-titre ne déborde jamais au-delà d'un
  changement de plan sur le plan de la personne suivante.
- **Attentif aux locuteurs :** répliques de dialogue avec tirets, une ligne par locuteur.
- **Doublage :** une voix Gemini naturelle par locuteur (choisie selon la hauteur de voix), un clone
  vocal local de chaque locuteur (VoxCPM2), des voix de studio ou Fish Audio. Un script vocal
  distinct écrit les noms tels qu'ils se prononcent et les nombres en toutes lettres, pour que la
  voix les dise correctement.
- **Trois façons de l'utiliser :** un menu clic droit dans le navigateur (« ترجم للعربية »), une
  page web locale ou une conversation : ajoutez tarjim à l'application Claude, à Claude Code ou à
  Codex et demandez-lui de traduire un lien.

## Connecter une IA : trois façons

| Façon | Choix | Remarques |
|---|---|---|
| Clé d'API | Gemini, OpenAI, Anthropic, OpenRouter, DeepSeek, Qwen, Mistral, Groq, xAI ou toute adresse compatible OpenAI | Gemini et OpenAI peuvent aussi écouter (reconnaissance vocale). |
| Votre abonnement | Claude (via Claude Code), ChatGPT (via Codex), Grok (via Grok Build), GitHub Copilot, Google AI (via Antigravity) | tarjim lance le programme du fournisseur lui-même avec votre connexion. L'utilisation est décomptée de votre forfait et les conditions de chaque fournisseur s'appliquent. |
| Sur votre ordinateur | Ollama, LM Studio, Jan, llama.cpp, vLLM, KoboldCpp | Détectés automatiquement avec leurs modèles. Rien ne quitte votre appareil. |

Choisissez n'importe quel modèle proposé par un fournisseur. Si le moteur choisi échoue ou épuise
son quota, tarjim se rabat sur le moteur local lorsqu'il y en a un.

## Ce dont votre ordinateur a besoin

Les parties lourdes sont facultatives. Ce qu'il vous faut dépend des parties qui tournent sur votre
propre ordinateur :

| Ce que vous utilisez | Carte graphique | Mémoire (RAM) | Disque libre |
|---|---|---|---|
| Sous-titres avec une IA que vous connectez (une clé Gemini, un abonnement Claude ou ChatGPT, n'importe quelle clé d'API) | Inutile | 8 Go | environ 6 Go |
| Doublage avec des voix naturelles ou de studio | Inutile | 8 Go | rien de plus |
| Écoute sur cet ordinateur (l'audio ne le quitte jamais) | NVIDIA, 8 Go | 16 Go | 6.3 Go de plus |
| Traduction sur cet ordinateur (Ollama avec aya-expanse 8B) | 8 Go | 16 Go | 5.1 Go de plus |
| Doublage avec la voix propre de chaque locuteur | NVIDIA, 8 Go | 16 Go | 4.7 Go de plus |

- **Système :** Windows 10 ou 11, 64 bits. macOS et Linux exécutent le même code, mais n'ont pas
  encore été testés.
- **Internet :** pour les téléchargements et pour l'IA que vous connectez. Avec l'écoute et la
  traduction sur cet ordinateur, les tâches s'exécutent hors ligne une fois tout téléchargé.
- **Sans carte NVIDIA**, tout fonctionne quand même sur le processeur, mais beaucoup plus lentement
  ; le doublage avec la voix propre du locuteur n'y est pas praticable.
- **Un modèle à la fois :** tarjim libère chaque modèle avant de charger le suivant, si bien que la
  carte graphique doit avoir de la place pour le plus gros (environ 6 Go), pas pour tous ensemble.
- **Tout sur cet ordinateur :** environ 22 Go de disque.

Mesuré sous Windows 11 avec une RTX 5080 (16 Go) et 32 Go de RAM : l'écoute sur la carte a atteint
au plus 5.9 Go de mémoire graphique, la traduction avec aya-expanse 8B 5.7 Go et la voix propre du
locuteur 6.1 Go, à raison d'environ 3 secondes par phrase. Le chargement du modèle de voix du
locuteur occupe brièvement environ 11 Go de RAM avant de se stabiliser à 2.5 Go, ce qui explique les
16 Go demandés. Le moteur lui-même (Python avec la version de PyTorch pour carte graphique) occupe
environ 4 Go des chiffres de disque ci-dessus.

## Installer avec votre IA (une seule étape)

Dans Claude Code :

```bash
claude plugin marketplace add willynilly0085-creator/tarjim
claude plugin install tarjim@tarjim
```

Dites ensuite à votre IA « installe tarjim ». Elle installe le moteur en arrière-plan (la version
pour carte graphique si vous avez une carte NVIDIA), le démarre sans ouvrir de fenêtre et ouvre la
page de configuration. Dès lors, votre IA utilise directement les outils de tarjim : « traduis ce
lien en français et incruste les sous-titres », « utilise mon abonnement Claude pour la
traduction », « passe au modèle local ». tarjim est un outil que votre IA manipule, pas un
assistant de plus avec qui discuter. Le plugin nécessite [uv](https://docs.astral.sh/uv/).

Autres applications MCP (Codex, Cursor, etc.) : une fois le moteur installé, ajoutez la commande
`tarjim-mcp` comme serveur MCP, par exemple `codex mcp add tarjim -- tarjim-mcp`. Codex vous demande
d'approuver chaque appel d'outil ; pour que les outils de tarjim s'exécutent sans demander, ajoutez
`default_tools_approval_mode = "approve"` sous `[mcp_servers.tarjim]` dans `~/.codex/config.toml`.

Testé : une session Claude Code avec le plugin a lu les réglages, défini le glossaire, traduit un
lien YouTube en espagnol et renvoyé les sous-titres ; Codex (forfait ChatGPT) a lu les réglages et
défini le glossaire. Le site web et l'application de bureau ChatGPT ne peuvent pas encore accéder
aux outils de votre ordinateur (ils n'acceptent que des serveurs MCP distants) : utilisez donc
Codex pour ChatGPT.

## Installation manuelle (Windows)

Nécessite Python 3.11. Disque, mémoire et carte graphique : voir [Ce dont votre ordinateur a besoin](#ce-dont-votre-ordinateur-a-besoin).

```powershell
git clone https://github.com/willynilly0085-creator/tarjim
cd tarjim
python -m venv .venv
# NVIDIA graphics card: install the CUDA build of PyTorch first (the default one is CPU only)
.venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python -m pip install -e ".[dub]"
.venv\Scripts\tarjim-serve
```

Ouvrez <http://127.0.0.1:17653>. La page de configuration vérifie votre appareil, connecte une IA
et télécharge ce dont vous avez besoin, y compris ffmpeg (sous Windows, il est téléchargé puis
vérifié à l'aide de son empreinte SHA-256 publiée). Sans carte graphique utilisable, tout
fonctionne quand même sur le processeur, simplement plus lentement.

**macOS et Linux** suivent les mêmes étapes avec `.venv/bin/...`, plus `brew install ffmpeg` ou
`sudo apt install ffmpeg`. Ces plateformes n'ont pas encore été testées.

### Extension de navigateur

tarjim vit dans votre navigateur : faites un clic droit sur n'importe quelle vidéo ou n'importe
quel lien et choisissez **ترجم للعربية** (ou votre langue), puis choisissez sous-titres,
sous-titres incrustés ou doublage. La fenêtre contextuelle affiche l'étape de chaque tâche et
permet de la mettre en pause, de l'annuler ou d'ouvrir le résultat.

Dans Chrome, ouvrez `chrome://extensions`, activez **Developer mode** (mode développeur), choisissez
**Load unpacked** (charger l'extension non empaquetée) et sélectionnez le dossier `~/.tarjim/extension`.
L'extension s'appaire toute seule : cliquez sur **Allow** (autoriser) sur la page de tarjim.

### Conversation

Sur la page de configuration, à l'étape « Use tarjim from a chat » (utiliser tarjim depuis une
conversation), cliquez sur **Add** (ajouter) à côté de l'application Claude, de Claude Code ou de
Codex. Votre IA peut alors piloter tout l'outil pour vous :

- « Traduis ce lien en arabe et double-le », « où en est-il ? », « mets-le en pause », « ouvre le résultat » ;
- modifier les réglages : « utilise mon abonnement Claude pour la traduction », « passe au modèle
  local », « liste les IA que je peux connecter », « mets l'interface en anglais » ;
- vous relire les sous-titres terminés, relancer une tâche qui a échoué ou télécharger un outil manquant.

Les clés ne sont jamais saisies dans la conversation ; pour cela, l'IA ouvre la page de tarjim.

### Téléphone

Envoyez un lien vidéo à votre propre bot Telegram depuis n'importe quel téléphone, iPhone ou
Android, chez vous ou en déplacement, et la vidéo traduite revient dans la même conversation. Dans
les Réglages, ouvrez **Téléphone** : créez un bot dans BotFather (`/newbot`), collez son jeton (il
reste dans le coffre de votre ordinateur), puis scannez le code QR avec votre téléphone et appuyez
sur **Démarrer**. Le bot ne répond qu'à votre compte, et c'est votre ordinateur qui demande à
Telegram les nouveaux messages : aucun port n'est donc ouvert sur internet. La langue, le résultat
et le style viennent des Réglages ; `/mode` dans le bot change le résultat. Telegram autorise les
bots à télécharger des vidéos jusqu'à 20 Mo et à envoyer des fichiers jusqu'à 50 Mo : un résultat
plus gros est réencodé pour tenir, ou vous recevez le fichier de sous-titres et la vidéo complète
reste sur votre ordinateur. Le bot répond tant que votre ordinateur et tarjim fonctionnent.

### Ligne de commande

```bash
tarjim video.mp4                 # Arabic (Saudi), burned into the video
tarjim video.mp4 --to fr         # any target language
tarjim video.mp4 --no-burn       # .srt and .ass only
```

## Mises à jour

tarjim se maintient à jour tout seul. Une fois par jour, le moteur demande à GitHub le numéro de la
dernière version : une seule requête qui ne transporte rien sur vous ni sur vos vidéos. Lorsque
**Mettre tarjim à jour automatiquement** est activé (proposé pendant l'installation et modifiable
dans les Réglages), une version plus récente s'installe en arrière-plan tant qu'aucune tâche n'est
en cours, et tarjim revient tout seul en quelques minutes ; l'extension du navigateur se recharge
d'elle-même pour rester alignée. Lorsque l'option est désactivée, la page affiche un avis et un
bouton **Mettre à jour**. Une copie lancée depuis le code source se met à jour avec `git pull`.

## Confidentialité et sécurité

- **Les clés** sont stockées dans le coffre chiffré de votre système d'exploitation (Gestionnaire
  d'identification de Windows, Trousseau de macOS, Secret Service). Le fichier de réglages n'en
  contient aucune.
- **Ce qui quitte votre appareil** dépend de votre mode de connexion : l'audio de l'extrait est
  envoyé au fournisseur d'écoute que vous avez choisi, et le texte aux fournisseurs de traduction
  et de voix que vous avez choisis. En mode local, rien ne sort : cela a été mesuré en surveillant
  chaque connexion pendant une tâche locale complète, doublage compris (zéro connexion externe). Les
  modèles se chargent hors ligne ; internet n'est utilisé que lorsque vous téléchargez un outil.
- **Le serveur local** n'écoute que sur 127.0.0.1. Chaque requête exige un jeton ou le cookie
  same-site de la page, les en-têtes `Host` étrangers sont refusés (DNS rebinding), les sites web ne
  peuvent ni l'atteindre ni demander un appairage, et il ne sert aucun fichier en dehors de ses
  propres dossiers.

Consultez [SECURITY.md](SECURITY.md) pour signaler un problème.

## Licences des modèles

Le code de tarjim n'inclut pas les poids des modèles ; vous les téléchargez auprès de leurs
propriétaires. Certains **ne sont pas autorisés pour un usage commercial** :

| Outil | Licence | Usage commercial |
|---|---|---|
| Aligneur de synchronisation `MahmoudAshraf/mms-300m-1130-forced-aligner` (obligatoire) | CC-BY-NC-4.0 | Non |
| Clonage vocal VoxCPM2 (facultatif) | Apache-2.0 | Oui |
| Traduction locale `aya-expanse:8b` (facultatif) | CC-BY-NC-4.0 | Non |
| Écoute locale Qwen3-ASR-1.7B et Qwen3-ForcedAligner | Apache-2.0 | Oui |
| ffmpeg (version LGPL) | LGPL-2.1 | Oui |

La page de configuration affiche chaque licence à côté du téléchargement correspondant.

## État

Testé sous Windows 11 avec une RTX 5080, ainsi qu'à partir d'une installation vierge sans prise en
charge graphique : liens et fichiers, sous-titres incrustés et `.srt`, français et arabe, pause,
reprise, annulation et relance, les trois façons de se connecter (abonnements Claude et ChatGPT,
Ollama en local), les outils de conversation, le doublage avec la voix propre du locuteur (de
l'anglais vers l'arabe saoudien) et les contrôles de sécurité ci-dessus. Pas encore testé : macOS,
Linux, les abonnements GitHub Copilot et Antigravity, et le bot du téléphone avec le service
Telegram réel (son code est couvert par des tests avec un Telegram simulé).

## Licence

tarjim est gratuit pour tous, entreprises comprises : utilisez-le, étudiez-le, modifiez-le et
partagez-le, à toutes fins. La seule chose interdite est de **le vendre** : personne ne peut vendre
tarjim, ni vendre un produit ou un service (hébergement et support payant compris) dont la valeur
provient de tarjim. Voir [LICENSE.md](LICENSE.md) ; le texte intégral, seul juridiquement
contraignant, se trouve en anglais dans [../../LICENSE](../../LICENSE) (Apache License 2.0 avec la
Commons Clause).

Les modèles que tarjim télécharge ont leurs propres licences, et certaines interdisent l'usage
commercial : consultez le tableau des licences des modèles ci-dessus avant d'utiliser ces modèles
dans un cadre professionnel.

## Développement

```bash
pip install -e ".[dub,dev]"
pytest && ruff check tarjim tests && mypy tarjim
```

Les décisions de conception et les mesures sont consignées dans [docs/decisions.md](../../docs/decisions.md).
Voir [CONTRIBUTING.md](CONTRIBUTING.md).
