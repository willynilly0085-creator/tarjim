# tarjim
<!-- languages -->
[English](../../README.md) · [العربية](../../i18n/ar/README.md) · [Español](../../i18n/es/README.md) · [Français](../../i18n/fr/README.md) · **Português** · [Deutsch](../../i18n/de/README.md) · [Русский](../../i18n/ru/README.md) · [Türkçe](../../i18n/tr/README.md) · [हिन्दी](../../i18n/hi/README.md) · [اردو](../../i18n/ur/README.md) · [Bahasa Indonesia](../../i18n/id/README.md) · [日本語](../../i18n/ja/README.md) · [中文](../../i18n/zh/README.md) · [한국어](../../i18n/ko/README.md)

Desenvolvido pela [Indicators](https://indicators.sa/) · [indicators.sa](https://indicators.sa/)

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
  local de cada locutor (VoxCPM2), vozes de estúdio ou Fish Audio. Um roteiro de voz separado
  escreve os nomes como são pronunciados e os números por extenso, para que a voz os diga
  corretamente.
- **Três formas de usar:** um menu de clique com o botão direito no navegador ("ترجم للعربية"), uma
  página web local ou um chat: adicione o tarjim ao app do Claude, ao Claude Code ou ao Codex e peça
  que ele traduza um link.

## Conecte uma IA: três formas

| Forma | Opções | Observações |
|---|---|---|
| Chave de API | Gemini, OpenAI, Anthropic, OpenRouter, DeepSeek, Qwen, Mistral, Groq, xAI ou qualquer endereço compatível com OpenAI | Gemini e OpenAI também podem escutar (fala para texto). |
| Sua assinatura | Claude (pelo Claude Code), ChatGPT (pelo Codex), Grok (pelo Grok Build), GitHub Copilot, Google AI (pelo Antigravity) | O tarjim executa o próprio programa do fornecedor com o seu login. O uso é descontado do seu plano e valem os termos de cada fornecedor. |
| No seu computador | Ollama, LM Studio, Jan, llama.cpp, vLLM, KoboldCpp | Detectados automaticamente com seus modelos. Nada sai do seu dispositivo. |

Escolha qualquer modelo que um provedor ofereça. Se o mecanismo escolhido falhar ou esgotar a
cota, o tarjim recorre ao mecanismo local quando houver um disponível.

## O que o seu computador precisa

As partes pesadas são opcionais. O que você precisa depende de quais partes são executadas no seu
próprio computador:

| O que você usa | Placa de vídeo | Memória (RAM) | Disco livre |
|---|---|---|---|
| Legendas com uma IA que você conecta (uma chave do Gemini, uma assinatura do Claude ou do ChatGPT, qualquer chave de API) | Não é necessária | 8 GB | cerca de 6 GB |
| Dublagem com vozes naturais ou de estúdio | Não é necessária | 8 GB | nada extra |
| Escuta neste computador (o áudio nunca sai dele) | NVIDIA, 8 GB | 16 GB | 6.3 GB a mais |
| Tradução neste computador (Ollama com aya-expanse 8B) | 8 GB | 16 GB | 5.1 GB a mais |
| Dublagem com a voz própria de cada locutor | NVIDIA, 8 GB | 16 GB | 4.7 GB a mais |

- **Sistema:** Windows 10 ou 11, 64 bits. macOS e Linux executam o mesmo código, mas ainda não foram
  testados.
- **Internet:** para os downloads e para a IA que você conecta. Com a escuta e a tradução neste
  computador, os trabalhos rodam offline depois que tudo foi baixado.
- **Sem uma placa NVIDIA**, tudo continua funcionando no processador, só que bem mais devagar; a
  dublagem com a voz própria do locutor não é prática nesse caso.
- **Um modelo por vez:** o tarjim libera cada modelo antes de carregar o próximo, então a placa de
  vídeo precisa de espaço para o maior (cerca de 6 GB), não para todos juntos.
- **Tudo neste computador:** cerca de 22 GB de disco.

Medido no Windows 11 com uma RTX 5080 (16 GB) e 32 GB de RAM: a escuta na placa chegou ao pico de
5.9 GB de memória de vídeo, a tradução com aya-expanse 8B a 5.7 GB e a voz própria do locutor a 6.1
GB, com cerca de 3 segundos por frase. Carregar o modelo da voz do locutor ocupa por pouco tempo
cerca de 11 GB de RAM antes de se estabilizar em 2.5 GB, e é por isso que ele pede 16 GB. O motor em
si (Python com a versão do PyTorch para placa de vídeo) ocupa cerca de 4 GB dos valores de disco
acima.

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

Requer Python 3.11. Disco, memória e placa de vídeo: veja [O que o seu computador precisa](#o-que-o-seu-computador-precisa).

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
**Load unpacked** (carregar sem compactação) e selecione a pasta `~/.tarjim/extension`. A extensão faz o
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

### Celular

Envie um link de vídeo para o seu próprio bot do Telegram de qualquer celular, iPhone ou Android,
em casa ou fora, e o vídeo traduzido volta no mesmo chat. Em Configurações, abra **Celular**:
crie um bot no BotFather (`/newbot`), cole o token dele (que fica no cofre do seu computador),
depois escaneie o código QR com o celular e toque em **Iniciar**. O bot responde apenas à sua
conta, e é o seu computador que pergunta ao Telegram por novas mensagens, então nenhuma porta é
aberta para a internet. O idioma, o resultado e o estilo vêm de Configurações; `/mode` no bot
muda o resultado. O Telegram permite que bots baixem vídeos de até 20 MB e enviem arquivos de até
50 MB: um resultado maior é recodificado para caber, ou você recebe o arquivo de legendas e o
vídeo completo continua no seu computador. O bot responde enquanto o seu computador e o tarjim
estiverem em execução.

### Linha de comando

```bash
tarjim video.mp4                 # Arabic (Saudi), burned into the video
tarjim video.mp4 --to fr         # any target language
tarjim video.mp4 --no-burn       # .srt and .ass only
```

## Atualizações

O tarjim se mantém atualizado sozinho. Uma vez por dia o motor pergunta ao GitHub o número da versão
mais recente: uma única requisição que não leva nada sobre você nem sobre seus vídeos. Com
**Atualizar o tarjim automaticamente** ativado (oferecido durante a configuração e alterável em
Configurações), uma versão mais nova é instalada em segundo plano enquanto nenhuma tarefa está em
andamento, e o tarjim volta sozinho em alguns minutos; a extensão do navegador se recarrega sozinha
para acompanhar. Com a opção desativada, a página mostra um aviso e um botão **Atualizar agora**.
Uma cópia que você executa a partir do código-fonte é atualizada com `git pull`.

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
| Clone de voz VoxCPM2 (opcional) | Apache-2.0 | Sim |
| Tradução local `aya-expanse:8b` (opcional) | CC-BY-NC-4.0 | Não |
| Escuta local Qwen3-ASR-1.7B e Qwen3-ForcedAligner | Apache-2.0 | Sim |
| ffmpeg (build LGPL) | LGPL-2.1 | Sim |

A página de configuração mostra cada licença ao lado do respectivo download.

## Status

Testado no Windows 11 com uma RTX 5080 e a partir de uma instalação limpa sem suporte gráfico:
links e arquivos, legendas gravadas e `.srt`, francês e árabe, pausar, retomar, cancelar e tentar
de novo, as três formas de conexão (assinaturas do Claude e do ChatGPT, Ollama local), as
ferramentas de chat, a dublagem com a voz própria do locutor (do inglês para o árabe saudita) e
as verificações de segurança acima. Ainda não testado: macOS, Linux, as assinaturas do GitHub
Copilot e do Antigravity e o bot do celular com o serviço real do Telegram (o código dele é
coberto por testes com um Telegram simulado).

## Licença

O tarjim é gratuito para todos, empresas incluídas: use, estude, modifique e compartilhe, para
qualquer finalidade. A única coisa proibida é **vendê-lo**: ninguém pode vender o tarjim, nem
vender um produto ou serviço (incluindo hospedagem e suporte pago) cujo valor venha do tarjim. Veja
[LICENSE.md](LICENSE.md); o texto completo e vinculante, em inglês, está em
[../../LICENSE](../../LICENSE) (Apache License 2.0 com a Commons Clause).

Os modelos que o tarjim baixa têm licenças próprias, e algumas proíbem o uso comercial: confira a
tabela de licenças dos modelos acima antes de usar esses modelos no trabalho.

## Desenvolvimento

```bash
pip install -e ".[dub,dev]"
pytest && ruff check tarjim tests && mypy tarjim
```

As decisões de design e as medições ficam registradas em [docs/decisions.md](../../docs/decisions.md).
Veja [CONTRIBUTING.md](CONTRIBUTING.md).
