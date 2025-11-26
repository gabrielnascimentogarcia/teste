# Simulador MIC-1 Profissional

Este é um simulador didático e visual da microarquitetura **MIC-1**, projetado para auxiliar no estudo de Organização e Arquitetura de Computadores. Ele permite escrever código em Assembly, montá-lo e visualizar a execução passo a passo no caminho de dados (datapath), com detalhes sobre registradores, barramentos, ULA (ALU), Shifter e Memória (incluindo Caches L1).

## 📋 Pré-requisitos

Para rodar este simulador, você precisa ter instalado:

*   **Python 3.8** ou superior.
*   **Tkinter**: Biblioteca gráfica padrão do Python.
    *   *Windows/macOS*: Geralmente já vem instalado com o Python.
    *   *Linux*: Pode ser necessário instalar separadamente (ex: `sudo apt-get install python3-tk`).

## 🚀 Como Rodar

1.  Abra o terminal na pasta raiz do projeto (`Simulador_MIC1`).
2.  Execute o arquivo principal:

```bash
python main.py
```

*(Se o comando `python` não funcionar, tente `python3` ou `py`).*

## 🖥️ Interface e Funcionalidades

A interface é dividida em três painéis principais:

### 1. Editor Assembly (Esquerda)
*   Área para escrever seu código Assembly.
*   Já vem com um código de exemplo carregado.
*   **Botão "Montar (Assemble)"**: Compila o código e carrega na memória. **Sempre clique aqui após alterar o código.**

### 2. Datapath / Microarquitetura (Centro)
*   Visualização gráfica da CPU.
*   **Registradores**: MAR, MDR, PC, MBR, SP, LV, CPP, TOS, OPC, H.
*   **Barramentos**: Bus A, Bus B, Bus C.
*   **Animação**: Durante a execução, os componentes e barramentos ativos ficam **vermelhos**, indicando o fluxo de dados.

### 3. Controles e Memória (Direita)
*   **Painel de Controle**:
    *   **Run**: Executa o programa continuamente.
    *   **Step**: Executa um **micro-passo** (veja detalhes abaixo).
    *   **Stop**: Pausa a execução.
    *   **Reset**: Reinicia a CPU e limpa o estado visual.
    *   **Speed**: Ajusta a velocidade da animação.
    *   **Visualização (HEX/DEC)**: Alterna a exibição dos valores entre Hexadecimal e Decimal.
*   **Caches L1**: Mostra o estado das caches de Instrução (I-Cache) e Dados (D-Cache).
*   **Memória Principal**: Lista todo o conteúdo da RAM (4096 palavras).
    *   **Dica**: Você pode dar **duplo clique** em uma linha da memória para editar seu valor manualmente.

## ⚙️ Detalhes Importantes (Para não se confundir)

### O Botão "Step" e os Micro-passos
Diferente de alguns depuradores que executam uma linha de código inteira por vez, este simulador mostra o **ciclo de microinstrução**. Cada instrução Assembly é quebrada em 4 fases visuais:

1.  **BUSCA (Fetch)**: O endereço da próxima instrução (PC) é enviado para a memória.
2.  **DECODIFICAÇÃO (Decode)**: A instrução é lida da memória e decodificada.
3.  **EXECUÇÃO (Execute)**: A operação real acontece na ULA (ALU) e Shifter.
4.  **GRAVAÇÃO (Write Back)**: O resultado é escrito no registrador de destino ou memória.

Portanto, você precisará clicar em "Step" **4 vezes** para completar uma única instrução Assembly (como `LODD` ou `ADDD`).

### Cores na Memória
*   **Azul Claro**: Indica onde está o **PC** (Próxima instrução).
*   **Vermelho Claro**: Indica onde está o **SP** (Stack Pointer).
*   **Amarelo Claro**: Indica o último endereço acessado (leitura ou escrita).

### Caches
O simulador implementa uma **Split L1 Cache** (separada para Instruções e Dados).
*   **Valid**: Indica se a linha da cache contém dados válidos (1) ou lixo (0).
*   **Tag**: Parte do endereço usada para identificar o dado.
*   **Data**: O valor armazenado.

## 🛠️ Resolução de Problemas

*   **Erro "ModuleNotFoundError: No module named 'tkinter'"**: Instale o Tkinter (veja a seção de Pré-requisitos).
*   **O código não roda após edição**: Lembre-se de clicar em **"Montar (Assemble)"** sempre que mudar o texto no editor.
*   **A tela travou**: Clique em "Stop" ou feche e abra novamente. Se houver um loop infinito no seu Assembly (`JUMP Inicio`), o "Run" ficará rodando para sempre até você parar.

---
*Desenvolvido para fins educacionais.*
