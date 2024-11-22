```markdown
# Guia de Instalação do Projeto (Windows)

## Pré-requisitos
- Python instalado e configurado no PATH
- Git para Windows instalado
- Conta GitHub configurada com chave SSH

## Passo a Passo da Instalação

1. Clone o repositório:
```bash
git clone git@github.com:francislibra/projreforco.git
```

2. Entre na pasta do projeto:
```bash
cd projreforco
```

3. Crie um ambiente virtual:
```bash
projereforco> python -m venv .venv
```

4. Ative o ambiente virtual:
```bash
projreforco> .venv\Scripts\activate
```
> Após a ativação, você verá `(.venv)` no início do seu prompt de comando

5. Instale as dependências:
```bash
projreforco> pip install -r requirements.txt
```

6. Execute a aplicação:
```bash
projreforco> python app.py
```

## Problemas Comuns & Soluções

### Se aparecer erro de "Execution Policy"
Abra o PowerShell como Administrador e execute:
```powershell
Set-ExecutionPolicy RemoteSignned
```

### Se o Python não for reconhecido
- Verifique se o Python está instalado executando: `python --version`
- Se estiver instalado mas não for reconhecido, adicione o Python ao PATH:
  1. Pesquise por "Variáveis de Ambiente" no Windows
  2. Em Variáveis do Sistema, selecione "Path"
  3. Adicione o diretório de instalação do Python (geralmente `C:\Users\SeuUsuário\AppData\Local\Programs\Python\Python3x\`)

### Se o pip não for reconhecido
- Tente executar: `python -m pip install -r requirements.txt`

## Dicas
- Use o PowerShell ou Prompt de Comando em vez do Git Bash para melhor compatibilidade
- Para desativar o ambiente virtual, digite: `deactivate`
- Para ver os pacotes instalados: `pip list`

## Estrutura do Proj
```
projreforco/
├── .venv/                  # Ambiente virtual (criado durante a instalação)
├── requirements.txt # Dependências do projeto
└── app.py                # Arquivo principal da aplicação
```


