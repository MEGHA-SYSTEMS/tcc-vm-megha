<h1>Firebase Admin SDK</h1>

<h2>1. Pré-requisitos</h2>

<p>Para utilizar o Firebase Admin SDK, é necessário:

- Ter um projeto no Firebase  
- Possuir uma conta de serviço gerada automaticamente  
- Ter um arquivo de credenciais (JSON)  
- Utilizar um ambiente compatível com o SDK  
</p>

<h2>2. Instalação do SDK</h2>

<p>O Firebase Admin SDK é instalado utilizando o seguinte comando:</p>

<img width="919" height="401" alt="Captura de tela 2026-04-21 134235" src="https://github.com/user-attachments/assets/0971c833-6b9e-4067-9a17-1e379b24ccbd" />

<h2>3. Inicialização do SDK</h2>

<p>A inicialização do SDK é responsável por conectar a aplicação ao Firebase.</p>

<img width="920" height="142" alt="Captura de tela 2026-04-21 134311" src="https://github.com/user-attachments/assets/fac95ef9-e169-46f7-952c-032f6ef4996a" />

<p>Após a inicialização, é possível acessar os serviços do Firebase.</p>

<h2>4. Autenticação com OAuth 2.0</h2>

<p>O SDK permite autenticação utilizando tokens.</p>

<img width="922" height="173" alt="Captura de tela 2026-04-21 134415" src="https://github.com/user-attachments/assets/6283baff-cb6e-4d78-b6f7-1b4c189d4ea8" />

<p>Existem dois tipos principais:

- Access Token: utilizado para acessar recursos (curta duração)  
- Refresh Token: utilizado para gerar novos tokens automaticamente  

O SDK gerencia esse processo de forma automática.
</p>

<h2>5. Uso em ambientes fora do Google</h2>

<p>Em ambientes que não são do Google, é necessário utilizar uma chave privada (arquivo JSON).

Para isso, deve-se configurar a variável de ambiente:


GOOGLE_APPLICATION_CREDENTIALS="caminho/arquivo.json"</p>

<img width="918" height="220" alt="Captura de tela 2026-04-21 134558" src="https://github.com/user-attachments/assets/0baa34fa-b4bc-4b8b-9686-68ac060bd43c" />

<p>Essa configuração permite que a aplicação seja autenticada corretamente.</p>

<h2>6. Inicialização de múltiplos aplicativos</h2>

<p>O SDK permite inicializar mais de um aplicativo com configurações diferentes.</p>

<img width="922" height="466" alt="Captura de tela 2026-04-21 134733" src="https://github.com/user-attachments/assets/e360079c-8f7c-4003-beaa-312e00481e5d" />

<p>Cada aplicativo mantém suas próprias configurações, permitindo trabalhar com múltiplos projetos.</p>

<h2>7. Testes com credenciais</h2>

<p>Para realizar testes locais, pode-se utilizar o seguinte comando:</p>

<img width="918" height="148" alt="Captura de tela 2026-04-21 134945" src="https://github.com/user-attachments/assets/bb254b21-352a-42d6-bf6b-2c357d4e3234" />

<p>Esse processo permite autenticar a aplicação utilizando credenciais locais.

Em alguns casos, é necessário informar o ID do projeto na inicialização.

Para especificar explicitamente o ID do projeto:
</p>

<img width="923" height="169" alt="Captura de tela 2026-04-21 144431" src="https://github.com/user-attachments/assets/57dfb569-1fdd-40c4-a9d2-951be1fb20d6" />
