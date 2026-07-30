# Roteiro de testes - PsiReal Clínica

Use este roteiro depois de publicar os arquivos e depois de qualquer mudanca no Supabase.

## 1. Testes como psicologa assinante

### Login e acesso
- [ ] Abrir `painel-tcc.html`
- [ ] Entrar com e-mail e senha de uma psi ativa
- [ ] Confirmar que dashboard, pacientes e aplicações mostram somente dados reais daquela conta
- [ ] Abrir `painel-psi.html`
- [ ] Entrar com e-mail e senha de uma psi ativa
- [ ] Confirmar que o nome da psi aparece no topo
- [ ] Confirmar que nao entra com senha errada
- [ ] Fechar e abrir de novo para ver se o comportamento de sessao esta coerente

### Geracao de links para pacientes
- [ ] Gerar link para um paciente teste com `YSQ-S3`
- [ ] Gerar link para o mesmo paciente teste com `GAD-7`
- [ ] Gerar link para o mesmo paciente teste com `PHQ-9`
- [ ] Confirmar que cada link abre a pagina correta
- [ ] Confirmar que o link pode ser copiado
- [ ] Confirmar que o botao de WhatsApp monta a mensagem corretamente

### Preenchimento pelo paciente
- [ ] Abrir cada link em aba anonima
- [ ] Preencher nome e nascimento quando houver campo
- [ ] Responder o `YSQ-S3` ate o final
- [ ] Responder o `GAD-7` ate o final
- [ ] Responder o `PHQ-9` ate o final
- [ ] Confirmar tela final de envio em cada instrumento
- [ ] No `PHQ-9`, marcar item 9 acima de zero e confirmar se aparece aviso de seguranca
- [ ] Tentar reenviar o mesmo link e confirmar se o sistema bloqueia ou trata corretamente link ja respondido

### Retorno ao painel da psi
- [ ] Voltar ao `painel-psi.html`
- [ ] Clicar em atualizar
- [ ] Confirmar que o paciente aparece apenas com os dados da propria psi
- [ ] Confirmar badges dos instrumentos respondidos
- [ ] Confirmar que a ultima aplicacao e os scores aparecem
- [ ] Confirmar que existem botoes:
  - [ ] `Abrir painel de esquemas` para YSQ-S3
  - [ ] `Dashboard de ansiedade` para GAD-7
  - [ ] `Dashboard de depressao` para PHQ-9

### Painel de esquemas
- [ ] Abrir `painel-esquemas.html`
- [ ] Confirmar login/autorizacao conforme fluxo atual
- [ ] Confirmar que aparecem somente respostas YSQ-S3 da psi correta
- [ ] Abrir paciente teste
- [ ] Conferir:
  - [ ] lista de esquemas
  - [ ] scores
  - [ ] grafico
  - [ ] observacoes/notas
  - [ ] mudanca de status `novo` para `visto`, se aplicavel
- [ ] Confirmar que o painel nao mistura dados de outra psi

### Dashboard de ansiedade
- [ ] Abrir `painel-instrumento.html?instrumento=GAD-7`
- [ ] Confirmar titulo `Dashboard de ansiedade`
- [ ] Confirmar score mais recente
- [ ] Confirmar grafico longitudinal se houver mais de uma aplicacao
- [ ] Repetir o GAD-7 para o mesmo paciente e confirmar que a evolucao aparece em ordem cronologica

### Dashboard de depressao
- [ ] Abrir `painel-instrumento.html?instrumento=PHQ-9`
- [ ] Confirmar titulo `Dashboard de depressao`
- [ ] Confirmar score mais recente
- [ ] Confirmar grafico longitudinal se houver mais de uma aplicacao
- [ ] Repetir o PHQ-9 para o mesmo paciente e confirmar que a evolucao aparece em ordem cronologica

## 2. Testes como admin

### Login e acesso
- [ ] Abrir `admin-contatos.html`
- [ ] Entrar na area restrita
- [ ] Confirmar que contatos e testes carregam sem erro

### Contatos comerciais
- [ ] Enviar um formulario de contato pelo site principal
- [ ] Enviar um formulario pela pagina de terapia
- [ ] Enviar um formulario pela pagina de supervisao
- [ ] Enviar um formulario pela pagina corporativa
- [ ] Confirmar que todos aparecem em `Contatos`
- [ ] Conferir campos: nome, WhatsApp, servico, pagina, status, nota
- [ ] Alterar status para:
  - [ ] novo
  - [ ] em_contato
  - [ ] concluido
  - [ ] convertido
  - [ ] arquivado
- [ ] Salvar nota interna
- [ ] Excluir um contato teste
- [ ] Confirmar filtros por status e busca

### Testes e inventarios
- [ ] Confirmar que `YSQ-S3`, `GAD-7` e `PHQ-9` aparecem na aba `Testes`
- [ ] Buscar pelo nome do paciente teste
- [ ] Conferir colunas de formulario/instrumento, psi_id, score e data
- [ ] Confirmar que os testes da psi aparecem, mas sem misturar dados de pacientes indevidos

### Painel de esquemas dentro do admin
- [ ] Abrir a secao de esquemas no admin
- [ ] Buscar o paciente teste
- [ ] Abrir a resposta YSQ-S3
- [ ] Conferir grafico, scores e detalhes
- [ ] Confirmar que o painel aparece dentro do admin, sem pedir senha separada

## 3. Testes de seguranca e isolamento

- [ ] Criar duas psis teste diferentes no Supabase Auth e na tabela `psis`
- [ ] Gerar respostas para as duas
- [ ] Entrar como Psi A e confirmar que nao ve pacientes da Psi B
- [ ] Entrar como Psi B e confirmar que nao ve pacientes da Psi A
- [ ] No `painel-tcc.html`, confirmar que contadores, pacientes, aplicações e atividade recente mudam ao trocar de conta
- [ ] Tentar abrir manualmente uma URL de paciente de outra psi e confirmar que nao ha exposicao indevida
- [ ] Confirmar que links de paciente usam token e nao expõem `psi_id`

## 4. Testes de navegacao e UX

- [ ] No desktop, conferir sidebar lateral do site publico
- [ ] No mobile, conferir menu lateral sem setas estranhas
- [ ] Abrir `PsiReal Clínica` e confirmar que ha `Voltar ao site`
- [ ] Abrir `Biblioteca PsiReal` e confirmar:
  - [ ] entrada a partir do site
  - [ ] retorno ao site
  - [ ] ida para `PsiReal Clínica`
- [ ] Confirmar que nenhum card ou texto corta no celular
- [ ] Testar pelo menos:
  - [ ] iPhone pequeno
  - [ ] Android medio
  - [ ] desktop largo

## 5. Evidencias para guardar

Guarde prints ou videos curtos de:
- [ ] login da psi
- [ ] geracao de cada link
- [ ] formulario preenchido
- [ ] painel da psi com os tres instrumentos
- [ ] painel de esquemas
- [ ] dashboard GAD-7
- [ ] dashboard PHQ-9
- [ ] admin contatos
- [ ] admin testes
- [ ] isolamento entre duas psis

## 6. Sinais de que ainda nao esta pronto para vender

- [ ] Qualquer psi consegue ver resposta de outra
- [ ] Formulario salva, mas nao aparece no painel
- [ ] YSQ aparece, mas GAD-7 ou PHQ-9 nao aparecem no hub
- [ ] Dashboard longitudinal nao ordena por data
- [ ] Admin nao consegue alterar status ou excluir contato
- [ ] Menu mobile ou cards cortam conteudo
- [ ] Link antigo aponta para pagina externa errada
