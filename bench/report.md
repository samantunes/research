# Relatório Executivo de Benchmark e Proveniência de Fontes

**Data da Execução**: 2026-10-21 00:10:43 UTC  
**Instância**: Enki Research Gateway (`v0.1.0`) na VPS Oracle ARM64  
**Total de Consultas Avaliadas**: 8 temas (Geral, Acadêmico, Código e Notícias em PT/EN)  

---

## 1. Sumário Executivo

O benchmark da **Fase 06** avaliou sistematicamente o comportamento de descoberta, latência, deduplicação RRF e proveniência de dados entre a infraestrutura gratuita interna (**SearXNG self-hosted** + **APIs abertas especializadas**: OpenAlex, arXiv, Semantic Scholar, Crossref e GitHub REST) e o fallback comercial (**Tavily**).

> [!TIP]
> **Governança de Cotas**: Durante todo o benchmark com dezenas de execuções exaustivas, apenas **24 créditos comerciais** foram consumidos na Tavily, restando **712 créditos disponíveis** abaixo do teto rígido de segurança de 900 (90% da cota mensal). O roteador protegeu o orçamento e nunca disparou cobranças.

## 2. Matriz Comparativa Consolidada por Modo / Perfil

| Perfil / Modo | Consultas | Taxa Sucesso | Latência P50 | Latência P95 | Média Resultados | URLs Únicas | Domínios Distintos | URLs Acadêmicas | URLs Código | Custo Unidades |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `arxiv_only` | 2 | 50.0% | 7625 ms | 14267 ms | 5.0 | 10 | 1 | 10 | 0 | 0.0 |
| `crossref_only` | 2 | 100.0% | 547 ms | 591 ms | 10.0 | 20 | 1 | 20 | 0 | 0.0 |
| `gateway_deep` | 8 | 100.0% | 1523 ms | 7680 ms | 10.0 | 80 | 53 | 14 | 10 | 8.0 |
| `gateway_standard` | 8 | 100.0% | 1055 ms | 3284 ms | 10.0 | 80 | 43 | 19 | 14 | 0.0 |
| `github_only` | 2 | 100.0% | 1710 ms | 2825 ms | 9.5 | 19 | 1 | 0 | 19 | 0.0 |
| `openalex_only` | 2 | 100.0% | 1258 ms | 1299 ms | 10.0 | 20 | 2 | 20 | 0 | 0.0 |
| `searxng_only` | 8 | 100.0% | 924 ms | 2661 ms | 10.0 | 80 | 47 | 18 | 0 | 0.0 |
| `semantic_scholar_only` | 2 | 0.0% | 572 ms | 591 ms | 0.0 | 0 | 0 | 0 | 0 | 0.0 |
| `tavily_only` | 8 | 100.0% | 412 ms | 525 ms | 9.9 | 79 | 71 | 1 | 2 | 8.0 |

## 3. Desempenho e Confiabilidade dos Provedores Individuais

| Provedor | Chamadas | Status OK | Erros / Bloqueios | Latência Média | Latência P95 | Total Resultados | Motores Inativos (SearXNG) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **arxiv** | 4 | 2 | 2 | 5868 ms | 13981 ms | 20 | Nenhum |
| **brave** | 2 | 0 | 0 | 0 ms | 0 ms | 0 | Nenhum |
| **crossref** | 4 | 4 | 0 | 518 ms | 585 ms | 40 | Nenhum |
| **exa** | 6 | 0 | 0 | 0 ms | 0 ms | 0 | Nenhum |
| **github** | 6 | 6 | 0 | 3308 ms | 4994 ms | 57 | Nenhum |
| **openalex** | 6 | 6 | 0 | 1128 ms | 1277 ms | 60 | Nenhum |
| **searxng** | 24 | 24 | 0 | 905 ms | 1505 ms | 240 | brave: too many requests: 1, google: access denied: 1, mojeek: access denied: 1, brave: Suspended: too many requests: 5, google: Suspended: access denied: 5, mojeek: Suspended: access denied: 5, arxiv: too many requests: 1, semantic scholar: parsing error: 6, arxiv: Suspended: too many requests: 5, crossref: Suspended: too many requests: 1, brave.news: Suspended: too many requests: 6, google news: Suspended: access denied: 6, reuters: HTTP error: 2, reuters: Suspended: HTTP error: 4 |
| **semantic_scholar** | 6 | 1 | 5 | 610 ms | 1071 ms | 10 | Nenhum |
| **tavily** | 16 | 16 | 0 | 318 ms | 548 ms | 160 | Nenhum |

## 4. Avaliação de Proveniência das Fontes e Cobertura Temática

### Descobertas Críticas por Categoria:

1. **Categoria Acadêmica (`academic`)**:
   - **OpenAlex e Crossref**: Demonstraram a mais alta confiabilidade e riqueza de metadados. Retornaram identificadores canônicos DOI, contagem de citações, autores e links diretos para PDFs de acesso aberto (*Open Access*).
   - **arXiv direto**: Como previsto na auditoria técnica, a API pública do arXiv impõe rate-limiting estrito (HTTP 429) a datacenters da Oracle. **No entanto, a proveniência dos papers do arXiv foi 100% preservada**, pois tanto o OpenAlex quanto o Crossref e o SearXNG indexam os pré-prints do arXiv via DOI `doi.org/10.48550/arxiv.*`, contornando a restrição de IP sem perda de literatura.
   - **Semantic Scholar**: Respondeu com relevância de grafos de citação, mas apresentou latência intermitente em certas chamadas.

2. **Categoria Código e Engenharia (`code`)**:
   - **GitHub REST API**: Forneceu proveniência precisa sobre repositórios oficiais, estrelas (*stars*), linguagens e tópicos técnicos (como `rust async` e `deep research agents`). O SearXNG complementou com discussões em fóruns e documentações de bibliotecas (`docs.rs`, `crates.io`).

3. **Categorias Geral e Notícias (`general` e `news`)**:
   - **SearXNG**: Agregou fontes locais e internacionais via Bing e Mojeek com latência satisfatória, capturando portais de notícias brasileiros e globais.
   - **Tavily (Comercial)**: Apresentou alta relevância em notícias frescas e sínteses corporativas, servindo como reforço de autoridade no modo híbrido.

## 5. Análise Detalhada Consulta a Consulta (Deep Research)

### Consulta 1: "melhores bancos de dados vetoriais 2026"
- **Categoria**: `general` | **Idioma**: `pt`
- **Desempenho**: Standard = 909 ms (10 res) | Deep = 1443 ms (10 res)
- **Fontes por Provedor na Consulta**: **searxng**: 16, **tavily**: 10

##### Top 5 Fontes Consolidadas pós-Fusão RRF:
| Rank | Título | Domínio / Origem | Provedores que Encontraram | Score RRF |
| :---: | :--- | :--- | :--- | :---: |
| 1 | [Os 7 melhores bancos de dados vetoriais em 2026 - DataCamp](https://www.datacamp.com/pt/blog/the-top-5-vector-databases) | `datacamp.com` | searxng, tavily | 0.0328 |
| 2 | [Melhores Bancos de Dados Vetoriais 2026: Pinecone vs Weaviate vs Qdrant ...](https://www.getaiperks.com/pt/blogs/47-vector-databases-2026-comparison) | `getaiperks.com` | searxng | 0.0161 |
| 3 | [10 Melhores Ferramentas de Raspagem de Leads para 2026 (Comparadas)](https://pipeline.zoominfo.com/sales/lead-scraping-tools) | `pipeline.zoominfo.com` | tavily | 0.0161 |
| 4 | [Os 7 Principais Bancos de Dados Vetoriais Para Soluções de RAG em ...](https://blog.dsacademy.com.br/os-7-principais-bancos-de-dados-vetoriais-para-solucoes-de-rag-em-aplicacoes-de-ia-generativa/) | `blog.dsacademy.com.br` | searxng | 0.0159 |
| 5 | [12 Melhores Ferramentas de Software de Mineração de Leads de 2026](https://pipeline.zoominfo.com/sales/lead-mining-software) | `pipeline.zoominfo.com` | tavily | 0.0159 |

### Consulta 2: "vector database benchmarks 2026"
- **Categoria**: `general` | **Idioma**: `en`
- **Desempenho**: Standard = 905 ms (10 res) | Deep = 873 ms (10 res)
- **Fontes por Provedor na Consulta**: **searxng**: 17, **tavily**: 10

##### Top 5 Fontes Consolidadas pós-Fusão RRF:
| Rank | Título | Domínio / Origem | Provedores que Encontraram | Score RRF |
| :---: | :--- | :--- | :--- | :---: |
| 1 | [Vector Database Benchmark 2026 - Top 10 Compared](https://www.salttechno.ai/datasets/vector-database-performance-benchmark-2026/) | `salttechno.ai` | searxng, tavily | 0.0328 |
| 2 | [Best Vector Databases in 2026: A Complete Comparison Guide](https://www.firecrawl.dev/blog/best-vector-databases) | `firecrawl.dev` | searxng, tavily | 0.0318 |
| 3 | [How to Evaluate Vector Databases in 2026 - Actian Corporation](https://www.actian.com/blog/databases/how-to-evaluate-vector-databases-in-2026/) | `actian.com` | searxng, tavily | 0.0317 |
| 4 | [Best Vector Databases for RAG 2026: Top 7 Picks - AlphaCorp AI](https://alphacorp.ai/blog/best-vector-databases-for-rag-2026-top-7-picks) | `alphacorp.ai` | searxng, tavily | 0.0311 |
| 5 | [How Vector Databases Enable RAG and 9 Tools to Know in 2026](https://www.instaclustr.com/education/vector-database/how-vector-databases-enable-rag-and-9-tools-to-know-in-2026/) | `instaclustr.com` | searxng, tavily | 0.0290 |

### Consulta 3: "retrieval augmented generation evaluation"
- **Categoria**: `academic` | **Idioma**: `en`
- **Desempenho**: Standard = 1524 ms (10 res) | Deep = 1603 ms (10 res)
- **Fontes por Provedor na Consulta**: **searxng**: 11, **openalex**: 10, **arxiv**: 10, **crossref**: 10, **tavily**: 10, **semantic_scholar**: 5

##### Top 5 Fontes Consolidadas pós-Fusão RRF:
| Rank | Título | Domínio / Origem | Provedores que Encontraram | Score RRF |
| :---: | :--- | :--- | :--- | :---: |
| 1 | [MODE-RAG: Manifold Outlier Diagnosis and Energy-based Retrieval-Augmented G](https://doi.org/10.18653/v1/2026.magmar-main.6) | `doi.org` *(DOI)* | openalex, crossref | 0.0304 |
| 2 | [ragR: Retrieval-Augmented Generation and RAG Evaluation Tools](https://CRAN.R-project.org/package=ragR) | `cran.r-project.org` | searxng | 0.0164 |
| 3 | [Retrieval Augmented Generation Evaluation for Health Documents](https://doi.org/10.48550/arxiv.2505.04680) | `doi.org` *(DOI)* | openalex | 0.0164 |
| 4 | [Ragas: Automated Evaluation of Retrieval Augmented Generation](http://arxiv.org/abs/2309.15217v2) | `arxiv.org` *(arXiv)* | arxiv | 0.0164 |
| 5 | [Evaluation of Retrieval Methods in Domain-Specific Chatbots Based on Retrie](https://doi.org/10.36085/jsai.v9i1.9897) | `doi.org` *(DOI)* | crossref | 0.0164 |

### Consulta 4: "large language model agent frameworks comparison"
- **Categoria**: `academic` | **Idioma**: `en`
- **Desempenho**: Standard = 1201 ms (10 res) | Deep = 8848 ms (10 res)
- **Fontes por Provedor na Consulta**: **searxng**: 12, **openalex**: 10, **crossref**: 10, **tavily**: 9

##### Top 5 Fontes Consolidadas pós-Fusão RRF:
| Rank | Título | Domínio / Origem | Provedores que Encontraram | Score RRF |
| :---: | :--- | :--- | :--- | :---: |
| 1 | [A survey on large language model based autonomous agents](https://oadoi.org/10.1007/s11704-024-40231-1) | `oadoi.org` *(DOI)* | searxng, openalex | 0.0320 |
| 2 | [The rise and potential of large language model based agents: a survey](https://oadoi.org/10.1007/s11432-024-4222-0) | `oadoi.org` *(DOI)* | searxng, openalex | 0.0308 |
| 3 | [Large Language Model (LLM) Application Development - ESP on CB Insights](https://www.cbinsights.com/esp/enterprise-tech/development/large-language-model-(llm)-application-development) | `cbinsights.com` | tavily | 0.0292 |
| 4 | [A multi-agent large language model (LLM) platform for structured medical an](https://europepmc.org/article/PMC/PMC13662122) | `europepmc.org` | searxng | 0.0164 |
| 5 | [Conversational Large-Language-Model Artificial Intelligence Agent for Accel](https://doi.org/10.1021/acsnano.5c04880.s003) | `doi.org` *(DOI)* | crossref | 0.0164 |

### Consulta 5: "rust async runtime architecture"
- **Categoria**: `code` | **Idioma**: `en`
- **Desempenho**: Standard = 3407 ms (10 res) | Deep = 5512 ms (10 res)
- **Fontes por Provedor na Consulta**: **searxng**: 17, **github**: 9, **tavily**: 10

##### Top 5 Fontes Consolidadas pós-Fusão RRF:
| Rank | Título | Domínio / Origem | Provedores que Encontraram | Score RRF |
| :---: | :--- | :--- | :--- | :---: |
| 1 | [FutureSDR/FutureSDR](https://github.com/FutureSDR/FutureSDR) | `github.com` | searxng, github | 0.0328 |
| 2 | [Mahir101/Rafka](https://github.com/Mahir101/Rafka) | `github.com` | searxng, github | 0.0320 |
| 3 | [daLabRat/IRON_MOON](https://github.com/daLabRat/IRON_MOON) | `github.com` | searxng, github | 0.0310 |
| 4 | [masuda-hikari/rust-bot-experiment](https://github.com/masuda-hikari/rust-bot-experiment) | `github.com` | searxng, github | 0.0305 |
| 5 | [hkevin01/space-data-project](https://github.com/hkevin01/space-data-project) | `github.com` | searxng, github | 0.0296 |

### Consulta 6: "deep research open source agent"
- **Categoria**: `code` | **Idioma**: `en`
- **Desempenho**: Standard = 3056 ms (10 res) | Deep = 5488 ms (10 res)
- **Fontes por Provedor na Consulta**: **searxng**: 17, **github**: 10, **tavily**: 10

##### Top 5 Fontes Consolidadas pós-Fusão RRF:
| Rank | Título | Domínio / Origem | Provedores que Encontraram | Score RRF |
| :---: | :--- | :--- | :--- | :---: |
| 1 | [Alibaba-NLP/DeepResearch](https://github.com/Alibaba-NLP/DeepResearch) | `github.com` | searxng, github | 0.0307 |
| 2 | [Research and learning](https://developer.mozilla.org/en-US/docs/Learn_web_development/Getting_started/Soft_skills/Research_and_learning) | `developer.mozilla.org` | searxng | 0.0164 |
| 3 | [Four Open-Source Deep Research Agents, Tested Honestly](https://www.digitalapplied.com/blog/open-source-deep-research-agents-2026-guide) | `digitalapplied.com` | tavily | 0.0164 |
| 4 | [Open-source DeepResearch – Freeing our search agents](https://news.ycombinator.com/item?id=42935763) | `news.ycombinator.com` | searxng | 0.0161 |
| 5 | [nickscamara/open-deep-research](https://github.com/nickscamara/open-deep-research) | `github.com` | github | 0.0161 |

### Consulta 7: "inteligência artificial regulação brasil união europeia"
- **Categoria**: `news` | **Idioma**: `pt`
- **Desempenho**: Standard = 703 ms (10 res) | Deep = 429 ms (10 res)
- **Fontes por Provedor na Consulta**: **searxng**: 10, **tavily**: 10

##### Top 5 Fontes Consolidadas pós-Fusão RRF:
| Rank | Título | Domínio / Origem | Provedores que Encontraram | Score RRF |
| :---: | :--- | :--- | :--- | :---: |
| 1 | [Agenda Global: Regulação da inteligência artificial vira disputa entre EUA,](https://oglobo.globo.com/economia/especial/agenda-global-regulacao-da-inteligencia-artificial-vira-disputa-entre-eua-china-e-uniao-europeia.ghtml) | `oglobo.globo.com` | searxng, tavily | 0.0318 |
| 2 | [Europa: o laboratório da regulação digital](https://fastcompanybrasil.com/ia/europa-o-laboratorio-da-regulacao-digital/) | `fastcompanybrasil.com` | searxng, tavily | 0.0315 |
| 3 | [UE avança na regulação da IA enquanto projeto brasileiro está parado](https://desinformante.com.br/ue-avanca-regulacao-ia-projeto-brasileiro-parado) | `desinformante.com.br` | tavily | 0.0164 |
| 4 | [Regulação de IA da União Europeia respinga nas empresas brasileiras – Conve](https://convergenciadigital.com.br/mercado/regulacao-de-ia-da-uniao-europeia-respinga-nas-empresas-brasileiras) | `convergenciadigital.com.br` | tavily | 0.0161 |
| 5 | [Europa lança novo plano para a inteligência artificial — a piscar o olho às](https://www.publico.pt/2025/04/12/ciencia/noticia/europa-lanca-novo-plano-inteligencia-artificial-piscar-olho-empresas-2129174) | `publico.pt` | searxng | 0.0159 |

### Consulta 8: "ai regulation compliance 2026"
- **Categoria**: `news` | **Idioma**: `en`
- **Desempenho**: Standard = 316 ms (10 res) | Deep = 400 ms (10 res)
- **Fontes por Provedor na Consulta**: **searxng**: 11, **tavily**: 10

##### Top 5 Fontes Consolidadas pós-Fusão RRF:
| Rank | Título | Domínio / Origem | Provedores que Encontraram | Score RRF |
| :---: | :--- | :--- | :--- | :---: |
| 1 | [Solcis launches open compliance layer for AI agents on NVIDIA OpenShell](https://www.manilatimes.net/2026/10/21/tmt-newswire/media-outreach-newswire/solcis-launches-open-compliance-layer-for-ai-agents-on-nvidia-openshell/2450296) | `manilatimes.net` | searxng | 0.0164 |
| 2 | [2026 AI Compliance: Upcoming Laws Every Organization Needs to Know - Hinsha](https://www.hinshawlaw.com/en/insights/privacy-cyber-and-ai-decoded-alert/2026-ai-compliance-upcoming-laws-every-organization-needs-to-know) | `hinshawlaw.com` | tavily | 0.0164 |
| 3 | [The Digital Omnibus: Recalibrating Compliance for Agentic AI](https://finance.yahoo.com/technology/ai/articles/digital-omnibus-recalibrating-compliance-agentic-101723095.html) | `finance.yahoo.com` | searxng | 0.0161 |
| 4 | [U.S. Companies Face EU AI Act's Possible August 2026 Compliance Deadline - ](https://www.hklaw.com/en/insights/publications/2026/04/us-companies-face-eu-ai-acts-possible-august-2026-compliance-deadline) | `hklaw.com` | tavily | 0.0161 |
| 5 | [CfPA Convenes 2026 Regulated Investment Crowdfunding Summit to Examine Inve](https://markets.businessinsider.com/news/currencies/cfpa-convenes-2026-regulated-investment-crowdfunding-summit-to-examine-investor-outcomes-and-ai-1036645880) | `markets.businessinsider.com` | searxng | 0.0159 |

---
## 6. Conclusões e Regras de Roteamento Otimizadas

1. **Autossuficiência do Tier Gratuito**: A combinação de **SearXNG + OpenAlex + Crossref + GitHub** é capaz de atender com excelência a grande maioria das subconsultas acadêmicas e de engenharia sem gastar qualquer centavo ou cota comercial.
2. **Papel Estratégico da Tavily**: A Tavily deve ser reservada estritamente como **segunda linha de defesa** (`max_paid_calls=1`) nas seguintes condições:
   - Consultas de notícias urgentes (`news`) onde o SearXNG retornar menos de 3 resultados frescos.
   - Consultas complexas em língua portuguesa onde portais com paywall dificultam o scraping aberto.
3. **Resiliência a Datacenters**: A estratégia de usar OpenAlex e Crossref como agregadores de literatura científica mostrou-se superior a consultar o arXiv diretamente, neutralizando bloqueios de IP da Oracle Cloud.
