# tarjim
<!-- languages -->
[English](../../README.md) · [العربية](../../i18n/ar/README.md) · [Español](../../i18n/es/README.md) · [Français](../../i18n/fr/README.md) · **Português** · [Deutsch](../../i18n/de/README.md) · [Русский](../../i18n/ru/README.md) · [Türkçe](../../i18n/tr/README.md) · [हिन्दी](../../i18n/hi/README.md) · [اردو](../../i18n/ur/README.md) · [Bahasa Indonesia](../../i18n/id/README.md) · [日本語](../../i18n/ja/README.md) · [中文](../../i18n/zh/README.md) · [한국어](../../i18n/ko/README.md)

**Legendas e dublagem para qualquer vídeo, no seu idioma, no seu próprio computador.**

Cole um link ou arraste um arquivo. O tarjim escuta, sincroniza cada fala com o momento exato em
que é dita, separa cada locutor, traduz para uma linguagem natural e grava as legendas no vídeo,
gera um `.srt` ou faz a dublagem com uma voz para cada locutor.

## O que ele faz

- **Qualquer fonte:** links do YouTube, do X e de outros sites (yt-dlp), ou qualquer arquivo de vídeo ou áudio no seu dispositivo.
- **34 idiomas de destino**, da direita para a esquerda e da esquerda para a direita. O árabe usa
  por padrão um dialeto saudita; o árabe padrão moderno está a um clique de distância.
- **Escuta cuidadosa:** o áudio é ouvido três vezes e cada palavra passa por votação, para que um
  único erro de escuta não chegue à legenda.
- **Sincronização exata:** as palavras são alinhadas ao áudio no seu computador (alinhamento forçado
  CTC mais detecção de atividade de voz). As legendas nunca atravessam um corte de cena e invadem a
  cena da próxima pessoa.
- **Atento aos locutores:** falas de diálogo com travessões, uma linha por locutor.
- **Dublagem:** uma voz natural do Gemini para cada locutor (escolhida pelo tom), um clone de voz
  local de cada locutor (XTTS-v2), vozes de estúdio ou Fish Audio. Um roteiro de voz separado
  escreve os nomes como são pronunciados e os números por extenso, para que a voz os diga
  corretamente.
- **Três formas de usar:** um menu de clique com o botão direito no navegador ("ترجم للعربية"), uma
  página web local ou um chat: adicione o tarjim ao app do Claude, ao Claude Code ou ao Codex e peça
  que ele traduza um link.

## Conecte uma IA: três formas

| Forma | Opções | Observações |
|---|---|---|
| Chave de API | Gemini, OpenAI, Anthropic, OpenRouter, DeepSeek, Qwen, Mistral, Groq, xAI ou qualquer endereço compatível com OpenAI | Gemini e OpenAI também podem escutar (fala para texto). |
| Sua assinatura | Claude (pelo Claude Code), ChatGPT (pelo Codex), GitHub Copilot, Google AI (pelo Antigravity) | O tarjim executa o próprio programa do fornecedor com o seu login. O uso é descontado do seu plano e valem os termos de cada fornecedor. |
| No seu computador | Ollama, LM Studio, Jan, llama.cpp, vLLM, KoboldCpp | Detectados automaticamente com seus modelos. Nada sai do seu dispositivo. |

Escolha qualquer modelo que um provedor ofereça. Se o mecanismo escolhido falhar ou esgotar a
cota, o tarjim recorre ao mecanismo local quando houver um disponível.

## Instalação com a sua IA (um passo)

No Claude Code:

```bash
claude plugin marketplace add willynilly0085-creator/tarjim
claude plugin install tarjim@tarjim
```

Depois diga à sua IA "configure o tarjim". Ela instala o mecanismo em segundo plano (a versão para
placa de vídeo, se você tiver uma placa NVIDIA), inicia-o sem abrir nenhuma janela e abre a página
de configuração. A partir daí, sua IA usa diretamente as ferramentas do tarjim: "traduza este link
para o francês e grave as legendas", "use minha assinatura do Claude para a tradução", "mude para o
modelo local". O tarjim é uma ferramenta que a sua IA opera, não mais um assistente para conversar.
O plugin precisa do [uv](https://docs.astral.sh/uv/).

Outros apps com MCP (Codex, Cursor e outros): depois de instalar o mecanismo, adicione o comando
`tarjim-mcp` como servidor MCP, por exemplo `codex mcp add tarjim -- tarjim-mcp`. O Codex pede que
você aprove cada chamada de ferramenta; para que as ferramentas do tarjim rodem sem perguntar,
adicione `default_tools_approval_mode = "approve"` em `[mcp_servers.tarjim]` no arquivo
`~/.codex/config.toml`.

Testado: uma sessão do Claude Code com o plugin leu as configurações, definiu o glossário, traduziu
um link do YouTube para o espanhol e devolveu as legendas; o Codex (plano do ChatGPT) leu as
configurações e definiu o glossário. O site e o app para desktop do ChatGPT ainda não conseguem
acessar ferramentas no seu computador (só aceitam servidores MCP remotos), então use o Codex para o
ChatGPT.

## Instalação manual (Windows)

Requer Python 3.11 e cerca de 10 GB de disco para os modelos locais.

```powershell
git clone https://github.com/willynilly0085-creator/tarjim
cd tarjim
python -m venv .venv
# NVIDIA graphics card: install the CUDA build of PyTorch first (the default one is CPU only)
.venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python -m pip install -e ".[dub]"
.venv\Scripts\tarjim-serve
```

Abra <http://127.0.0.1:17653>. A página de configuração verifica seu dispositivo, conecta uma IA e
baixa o que você precisa, incluindo o ffmpeg (no Windows ele é baixado e conferido com o SHA-256
publicado). Sem uma placa de vídeo utilizável, tudo continua funcionando no processador, só que
mais devagar.

**macOS e Linux** seguem os mesmos passos com `.venv/bin/...`, além de `brew install ffmpeg` ou
`sudo apt install ffmpeg`. Essas plataformas ainda não foram testadas.

### Extensão do navegador

O tarjim fica no seu navegador: clique com o botão direito em qualquer vídeo ou link e escolha
**ترجم للعربية** (ou o seu idioma), depois escolha legendas, legendas gravadas ou dublagem. O popup
mostra a etapa de cada tarefa e permite pausar, cancelar ou abrir o resultado.

No Chrome, abra `chrome://extensions`, ative o **Developer mode** (modo do desenvolvedor), escolha
**Load unpacked** (carregar sem compactação) e selecione a pasta `extension`. A extensão faz o
pareamento sozinha: clique em **Allow** (permitir) na página do tarjim.

### Chat

Na página de configuração, na etapa "Use tarjim from a chat" (usar o tarjim em um chat), clique em
**Add** (adicionar) ao lado do app do Claude, do Claude Code ou do Codex. A partir daí, sua IA pode
operar a ferramenta inteira por você:

- "Traduza este link para o árabe e faça a dublagem", "em que etapa está?", "pause", "abra o resultado";
- mudar as configurações: "use minha assinatura do Claude para a tradução", "mude para o modelo
  local", "liste as IAs que posso conectar", "deixe a interface em inglês";
- ler para você as legendas prontas, tentar de novo uma tarefa que falhou ou baixar uma ferramenta que esteja faltando.

As chaves nunca são digitadas pelo chat; para isso, a IA abre a página do tarjim.

### Linha de comando

```bash
tarjim video.mp4                 # Arabic (Saudi), burned into the video
tarjim video.mp4 --to fr         # any target language
tarjim video.mp4 --no-burn       # .srt and .ass only
```

## Privacidade e segurança

- **As chaves** ficam guardadas no cofre criptografado do seu sistema operacional (Gerenciador de
  Credenciais do Windows, Keychain do macOS, Secret Service). O arquivo de configurações não guarda
  nenhuma.
- **O que sai do seu dispositivo** depende da forma de conexão: o áudio do clipe vai para o
  provedor de escuta que você escolheu, e o texto vai para os provedores de tradução e de voz que
  você escolheu. No modo local nada sai: isso foi medido observando cada conexão durante uma tarefa
  local completa, com dublagem (zero conexões externas). Os modelos carregam offline; a internet só
  é usada quando você baixa uma ferramenta.
- **O servidor local** escuta apenas em 127.0.0.1. Toda requisição precisa de um token ou do cookie
  same-site da página, cabeçalhos `Host` externos são recusados (DNS rebinding), sites não conseguem
  acessá-lo nem pedir pareamento, e ele não serve nenhum arquivo fora das próprias pastas.

Veja [SECURITY.md](SECURITY.md) para relatar um problema.

## Licenças dos modelos

O código do tarjim não inclui os pesos dos modelos; você os baixa dos respectivos donos. Alguns
deles **não são licenciados para uso comercial**:

| Ferramenta | Licença | Uso comercial |
|---|---|---|
| Alinhador de sincronização `MahmoudAshraf/mms-300m-1130-forced-aligner` (obrigatório) | CC-BY-NC-4.0 | Não |
| Clone de voz XTTS-v2 (opcional, pede consentimento) | Coqui Public Model License | Não |
| Tradução local `aya-expanse:8b` (opcional) | CC-BY-NC-4.0 | Não |
| Escuta local Qwen3-ASR-1.7B e Qwen3-ForcedAligner | Apache-2.0 | Sim |
| ffmpeg (build LGPL) | LGPL-2.1 | Sim |

A página de configuração mostra cada licença ao lado do respectivo download.

## Status

Testado no Windows 11 com uma RTX 5080 e a partir de uma instalação limpa sem suporte gráfico:
links e arquivos, legendas gravadas e `.srt`, francês e árabe, pausar, retomar, cancelar e tentar
de novo, as três formas de conexão (assinaturas do Claude e do ChatGPT, Ollama local), as
ferramentas de chat e as verificações de segurança acima. Ainda não testado: macOS, Linux e as
assinaturas do GitHub Copilot e do Antigravity.

## Licença

O tarjim é livre para qualquer pessoa usar, estudar, modificar e compartilhar, para qualquer
finalidade **exceto uso comercial**: ninguém pode vendê-lo nem vender um serviço baseado nele. Veja
[LICENSE.md](LICENSE.md) (resumo da licença PolyForm Noncommercial 1.0.0); o texto completo e
vinculante, em inglês, está em [../../LICENSE.md](../../LICENSE.md). Isso está de acordo com as
licenças não comerciais dos modelos que ele usa.

## Desenvolvimento

```bash
pip install -e ".[dub,dev]"
pytest && ruff check tarjim tests && mypy tarjim
```

As decisões de design e as medições ficam registradas em [docs/decisions.md](../../docs/decisions.md).
Veja [CONTRIBUTING.md](CONTRIBUTING.md).
