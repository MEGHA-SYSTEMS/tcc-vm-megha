# modelo de dados  do cloud firestore
O Cloud Firestore é um banco de dados NoSQL que armazena dados em documentos organizados em coleções,em vez detabelas como no SQL.Cada documento contém pares de chave-valor e pode incluir dados simples ou estruturas mais complexas,como lista e objetos. O sistema é flexível,escalável e otimizado para armazenar muitos documentos pequenos.

# Documentos
No Cloud Firestore, a unidade de armazenamento é o documento. Um documento é um registro leve que contém campos, que são mapeados para valores. Cada documento é identificado por um nome.
Um documento que representa um usuário alovelace pode ser assim:
<img width="230" height="115" alt="Captura de tela 2026-04-21 210707" src="https://github.com/user-attachments/assets/7eb9eaa3-d632-4067-ab3d-edda21717fd3" />
Objetos complexos e aninhados em um documento são chamados de mapas. Por exemplo, é possível estruturar o nome do usuário do exemplo acima com um mapa, como este:
<img width="221" height="119" alt="Captura de tela 2026-04-21 210826" src="https://github.com/user-attachments/assets/2ce4bb23-0bad-465c-8643-530acd6b9a4c" />
Observe que os documentos parecem muito com documentos JSON. Na verdade, basicamente eles são. Há algumas diferenças, por exemplo, os documentos têm suporte a tipos de dados extras e são limitados ao limite de tamanho de documento. No entanto, geralmente os documentos podem ser tratados como registros JSON leves.

# Coleções
Os documentos pertencem a coleções, que são simplesmente recipientes para documentos. Por exemplo, é possível ter uma coleção users para conter seus vários usuários, cada um representado por um documento:
<img width="280" height="261" alt="Captura de tela 2026-04-21 211435" src="https://github.com/user-attachments/assets/ea6af486-7f9a-45af-8319-538ff10bffbf" />
O Cloud Firestore é um banco de dados sem esquema fixo, o que significa que você pode definir livremente os campos e tipos de dados em cada documento. Mesmo dentro da mesma coleção, os documentos podem ter estruturas diferentes, embora seja recomendado manter consistência para facilitar consultas.Coleções armazenam apenas documentos (não campos diretamente nem outras coleções). Cada documento tem um nome único, que pode ser definido por você ou gerado automaticamente.Não é necessário criar ou excluir coleções manualmente: elas surgem quando o primeiro documento é adicionado e deixam de existir quando todos os documentos são removidos.

# Referências
Cada documento no Cloud Firestore é identificado de maneira exclusiva pela respectiva localização no banco de dados. O exemplo anterior mostrou um documento alovelace na coleção users. Para se referir a este local no seu código, crie uma referência a ele.
<img width="953" height="109" alt="Captura de tela 2026-04-21 212048" src="https://github.com/user-attachments/assets/29102c8a-ffcc-48b9-93c3-f0abde3cb645" />
Uma referência é um objeto leve que aponta apenas para um local no banco de dados. É possível criar uma referência independentemente da existência de dados no banco de dados. A criação de uma referência não executa nenhuma operação de rede.
Você também pode criar referências a coleções:
<img width="940" height="99" alt="Captura de tela 2026-04-21 212216" src="https://github.com/user-attachments/assets/42b89d66-4bb9-4c5b-a681-fbcccbc00635" />
Para fins de praticidade, também é possível criar referências especificando o caminho para um documento ou uma coleção como uma string, com componentes de caminho separados por uma barra (/). Por exemplo, para criar uma referência ao documento alovelace:
<img width="1039" height="109" alt="Captura de tela 2026-04-21 212337" src="https://github.com/user-attachments/assets/5905bdd9-e3bc-4f27-9253-09b30b329ae7" />

# Dados hierárquicos
Para entender como as estruturas hierárquicas de dados funcionam no Cloud Firestore, pense em um exemplo de app de chat com mensagens e salas de conversa.
Crie um conjunto chamado rooms para armazenar salas de bate-papo diferentes:
<img width="311" height="173" alt="Captura de tela 2026-04-21 212735" src="https://github.com/user-attachments/assets/3a71e989-534b-41c8-8f7b-cd15197a6799" />
Agora que você tem salas de bate-papo, decida como armazenar suas mensagens. Talvez o documento da sala de bate-papo não seja uma boa escolha. Os documentos no Cloud Firestore devem ser leves, e uma sala de bate-papo pode conter um grande número de mensagens. No entanto, é possível criar coleções adicionais no documento da sala de bate-papo, como subcoleções.

# Subcoleções
A melhor maneira de armazenar mensagens neste cenário é usando subcoleções. Uma subcoleção é uma coleção associada a um documento específico.
É possível criar uma subcoleção chamada messages para cada documento da sala em sua coleção rooms:
<img width="329" height="332" alt="Captura de tela 2026-04-21 212931" src="https://github.com/user-attachments/assets/8eb620ac-9336-4bfc-a068-b65d88ab85a0" />
Neste exemplo, você criaria uma referência para uma mensagem na subcoleção com o seguinte código:
<img width="955" height="116" alt="Captura de tela 2026-04-21 213012" src="https://github.com/user-attachments/assets/e4760ca3-020c-4dbb-8aea-9d5e68aa2f10" />
Observe o padrão alternado de coleções e documentos. É importante que suas coleções e documentos sigam sempre esse padrão. Você não pode se referir a uma coleção em uma coleção ou a um documento em um documento.
As subcoleções permitem que você estruture os dados hierarquicamente, facilitando o acesso a eles. 
Para receber todas as mensagens em roomA, é possível criar uma referência de coleção para a subcoleção messages e interagir com ela como faria com outra referência de coleção.
Documentos em subcoleções também podem conter subcoleções, permitindo que os dados sejam mais aninhados. Você pode aninhar dados até 100 níveis.
