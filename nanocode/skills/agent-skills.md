# Agent Skills

Agent Skills are modular packages that extend Claude's capabilities with specialized domain knowledge, following Anthropic's [Agent Skills Specification](https://github.com/anthropics/skills/blob/main/agent_skills_spec.md). This plugin ecosystem includes **300+ local specialized skills** across 85 plugins, enabling progressive disclosure and efficient token usage.

## Overview

Skills provide Claude with deep expertise in specific domains without loading everything into context upfront. Each skill includes:

- **YAML Frontmatter**: Name and activation criteria
- **Progressive Disclosure**: Metadata → Instructions → Resources
- **Activation Triggers**: Clear "Use when" clauses for automatic invocation

## Skills by Plugin

### Kubernetes Operations (4 skills)

| Skill                      | Description                                                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **k8s-manifest-generator** | Create production-ready Kubernetes manifests for Deployments, Services, ConfigMaps, and Secrets following best practices |
| **helm-chart-scaffolding** | Design, organize, and manage Helm charts for templating and packaging Kubernetes applications                            |
| **gitops-workflow**        | Implement GitOps workflows with ArgoCD and Flux for automated, declarative deployments                                   |
| **k8s-security-policies**  | Implement Kubernetes security policies including NetworkPolicy, PodSecurityPolicy, and RBAC                              |

### LLM Application Development (8 skills)

| Skill                            | Description                                                                                 |
| -------------------------------- | ------------------------------------------------------------------------------------------- |
| **langchain-architecture**       | Design LLM applications using LangChain framework with agents, memory, and tool integration |
| **prompt-engineering-patterns**  | Master advanced prompt engineering techniques for LLM performance and reliability           |
| **rag-implementation**           | Build Retrieval-Augmented Generation systems with vector databases and semantic search      |
| **llm-evaluation**               | Implement comprehensive evaluation strategies with automated metrics and benchmarking       |
| **embedding-strategies**         | Design embedding pipelines for text, images, and multimodal content with optimal chunking   |
| **similarity-search-patterns**   | Implement efficient similarity search with ANN algorithms and distance metrics              |
| **vector-index-tuning**          | Optimize vector index performance with HNSW, IVF, and hybrid configurations                 |
| **hybrid-search-implementation** | Combine vector and keyword search for improved retrieval accuracy                           |

### Backend Development (9 skills)

| Skill                               | Description                                                                                           |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **api-design-principles**           | Master REST and GraphQL API design for intuitive, scalable, and maintainable APIs                     |
| **architecture-patterns**           | Implement Clean Architecture, Hexagonal Architecture, and Domain-Driven Design                        |
| **microservices-patterns**          | Design microservices with service boundaries, event-driven communication, and resilience              |
| **workflow-orchestration-patterns** | Design durable workflows with Temporal for distributed systems, saga patterns, and state management   |
| **temporal-python-testing**         | Test Temporal workflows with pytest, time-skipping, and mocking strategies for comprehensive coverage |
| **event-store-design**              | Design event stores with optimized schemas, snapshots, and stream partitioning                        |
| **cqrs-implementation**             | Implement CQRS with separate read/write models and eventual consistency patterns                      |
| **projection-patterns**             | Build efficient projections from event streams for read-optimized views                               |
| **saga-orchestration**              | Design distributed sagas with compensation logic and failure handling                                 |

### Developer Essentials (11 skills)

| Skill                            | Description                                                                                     |
| -------------------------------- | ----------------------------------------------------------------------------------------------- |
| **git-advanced-workflows**       | Master advanced Git workflows including rebasing, cherry-picking, bisect, worktrees, and reflog |
| **sql-optimization-patterns**    | Optimize SQL queries, indexing strategies, and EXPLAIN analysis for database performance        |
| **error-handling-patterns**      | Implement robust error handling with exceptions, Result types, and graceful degradation         |
| **code-review-excellence**       | Provide effective code reviews with constructive feedback and systematic analysis               |
| **e2e-testing-patterns**         | Build reliable E2E test suites with Playwright and Cypress for critical user workflows          |
| **auth-implementation-patterns** | Implement authentication and authorization with JWT, OAuth2, sessions, and RBAC                 |
| **debugging-strategies**         | Master systematic debugging techniques, profiling tools, and root cause analysis                |
| **monorepo-management**          | Manage monorepos with Turborepo, Nx, and pnpm workspaces for scalable multi-package projects    |
| **nx-workspace-patterns**        | Configure Nx workspaces with computation caching and affected commands                          |
| **turborepo-caching**            | Optimize Turborepo builds with remote caching and pipeline configuration                        |
| **bazel-build-optimization**     | Design Bazel builds with hermetic actions and remote execution                                  |

### Blockchain & Web3 (4 skills)

| Skill                       | Description                                                                             |
| --------------------------- | --------------------------------------------------------------------------------------- |
| **defi-protocol-templates** | Implement DeFi protocols with templates for staking, AMMs, governance, and flash loans      |
| **nft-standards**           | Implement NFT standards (ERC-721, ERC-1155) with metadata and marketplace integration   |
| **solidity-security**       | Master smart contract security to prevent vulnerabilities and implement secure patterns |
| **web3-testing**            | Test smart contracts using Hardhat and Foundry with unit tests and mainnet forking      |

### CI/CD Automation (4 skills)

| Skill                          | Description                                                                               |
| ------------------------------ | ----------------------------------------------------------------------------------------- |
| **deployment-pipeline-design** | Design multi-stage CI/CD pipelines with approval gates and security checks                |
| **github-actions-templates**   | Create production-ready GitHub Actions workflows for testing, building, and deploying     |
| **gitlab-ci-patterns**         | Build GitLab CI/CD pipelines with multi-stage workflows and distributed runners           |
| **secrets-management**         | Implement secure secrets management using Vault, AWS Secrets Manager, or native solutions |

### Cloud Infrastructure (8 skills)

| Skill                          | Description                                                               |
| ------------------------------ | ------------------------------------------------------------------------- |
| **terraform-module-library**   | Build reusable Terraform modules for AWS, Azure, and GCP infrastructure   |
| **multi-cloud-architecture**   | Design multi-cloud architectures avoiding vendor lock-in                  |
| **hybrid-cloud-networking**    | Configure secure connectivity between on-premises and cloud platforms     |
| **cost-optimization**          | Optimize cloud costs through rightsizing, tagging, and reserved instances |
| **istio-traffic-management**   | Configure Istio traffic routing, load balancing, and canary deployments   |
| **linkerd-patterns**           | Implement Linkerd service mesh with automatic mTLS and traffic splitting  |
| **mtls-configuration**         | Design zero-trust mTLS architectures with certificate management          |
| **service-mesh-observability** | Build comprehensive observability with distributed tracing and metrics    |

### Framework Migration (4 skills)

| Skill                   | Description                                                                   |
| ----------------------- | ----------------------------------------------------------------------------- |
| **react-modernization** | Upgrade React apps, migrate to hooks, and adopt concurrent features           |
| **angular-migration**   | Migrate from AngularJS to Angular using hybrid mode and incremental rewriting |
| **database-migration**  | Execute database migrations with zero-downtime strategies and transformations |
| **dependency-upgrade**  | Manage major dependency upgrades with compatibility analysis and testing      |

### Observability & Monitoring (4 skills)

| Skill                        | Description                                                             |
| ---------------------------- | ----------------------------------------------------------------------- |
| **prometheus-configuration** | Set up Prometheus for comprehensive metric collection and monitoring    |
| **grafana-dashboards**       | Create production Grafana dashboards for real-time system visualization |
| **distributed-tracing**      | Implement distributed tracing with Jaeger and Tempo to track requests   |
| **slo-implementation**       | Define SLIs and SLOs with error budgets and alerting                    |

### Payment Processing (4 skills)

| Skill                  | Description                                                                   |
| ---------------------- | ----------------------------------------------------------------------------- |
| **stripe-integration** | Implement Stripe payment processing for checkout, subscriptions, and webhooks |
| **paypal-integration** | Integrate PayPal payment processing with express checkout and subscriptions   |
| **pci-compliance**     | Implement PCI DSS compliance for secure payment card data handling            |
| **billing-automation** | Build automated billing systems for recurring payments and invoicing          |

### Python Development (16 skills)

| Skill                               | Description                                                                           |
| ----------------------------------- | ------------------------------------------------------------------------------------- |
| **async-python-patterns**           | Master Python asyncio, concurrent programming, and async/await patterns               |
| **python-testing-patterns**         | Implement comprehensive testing with pytest, fixtures, and mocking                    |
| **python-packaging**                | Create distributable Python packages with proper structure and PyPI publishing        |
| **python-performance-optimization** | Profile and optimize Python code using cProfile and performance best practices        |
| **uv-package-manager**              | Master the uv package manager for fast dependency management and virtual environments |

### JavaScript/TypeScript (4 skills)

| Skill                           | Description                                                                           |
| ------------------------------- | ------------------------------------------------------------------------------------- |
| **typescript-advanced-types**   | Master TypeScript's advanced type system including generics and conditional types     |
| **nodejs-backend-patterns**     | Build production-ready Node.js services with Express/Fastify and best practices       |
| **javascript-testing-patterns** | Implement comprehensive testing with Jest, Vitest, and Testing Library                |
| **modern-javascript-patterns**  | Master ES6+ features including async/await, destructuring, and functional programming |

### API Scaffolding (1 skill)

| Skill                 | Description                                                                     |
| --------------------- | ------------------------------------------------------------------------------- |
| **fastapi-templates** | Create production-ready FastAPI projects with async patterns and error handling |

### Machine Learning Operations (1 skill)

| Skill                    | Description                                                               |
| ------------------------ | ------------------------------------------------------------------------- |
| **ml-pipeline-workflow** | Build end-to-end MLOps pipelines from data preparation through deployment |

### Security Scanning (5 skills)

| Skill                               | Description                                                                     |
| ----------------------------------- | ------------------------------------------------------------------------------- |
| **sast-configuration**              | Configure Static Application Security Testing tools for vulnerability detection |
| **stride-analysis-patterns**        | Apply STRIDE methodology to identify spoofing, tampering, and other threats     |
| **attack-tree-construction**        | Build attack trees mapping threat scenarios to vulnerabilities                  |
| **security-requirement-extraction** | Derive security requirements from threat models with acceptance criteria        |
| **threat-mitigation-mapping**       | Map threats to mitigations with prioritized remediation plans                   |

### Accessibility Compliance (2 skills)

| Skill                     | Description                                                             |
| ------------------------- | ----------------------------------------------------------------------- |
| **wcag-audit-patterns**   | Conduct WCAG 2.2 accessibility audits with automated and manual testing |
| **screen-reader-testing** | Test screen reader compatibility across NVDA, JAWS, and VoiceOver       |

### Business Analytics (2 skills)

| Skill                    | Description                                                                  |
| ------------------------ | ---------------------------------------------------------------------------- |
| **kpi-dashboard-design** | Design executive dashboards with actionable KPIs and drill-down capabilities |
| **data-storytelling**    | Transform data insights into compelling narratives for stakeholders          |

### Before You Build (1 skill)

| Skill                | Description                                                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **before-you-build** | Review demand, positioning, monetization, retention, trust, distribution, and feature-adoption risk before implementation starts |

### Data Engineering (4 skills)

| Skill                           | Description                                                                 |
| ------------------------------- | --------------------------------------------------------------------------- |
| **spark-optimization**          | Optimize Apache Spark jobs with partitioning, caching, and broadcast joins  |
| **dbt-transformation-patterns** | Build dbt models with incremental strategies and testing                    |
| **airflow-dag-patterns**        | Design Airflow DAGs with proper dependencies and error handling             |
| **data-quality-frameworks**     | Implement data quality checks with Great Expectations and custom validators |

### Documentation Generation (3 skills)

| Skill                             | Description                                                         |
| --------------------------------- | ------------------------------------------------------------------- |
| **openapi-spec-generation**       | Generate OpenAPI 3.1 specifications from code with complete schemas |
| **changelog-automation**          | Automate changelog generation from conventional commits             |
| **architecture-decision-records** | Write ADRs documenting architectural decisions and trade-offs       |

### Frontend Mobile Development (4 skills)

| Skill                          | Description                                                     |
| ------------------------------ | --------------------------------------------------------------- |
| **react-state-management**     | Implement state management with Zustand, Jotai, and React Query |
| **nextjs-app-router-patterns** | Build Next.js 14+ apps with App Router, RSC, and streaming      |
| **tailwind-design-system**     | Create design systems with Tailwind CSS and component libraries |
| **react-native-architecture**  | Architect React Native apps with navigation and native modules  |

### UI Design (9 skills)

| Skill                         | Description                                                         |
| ----------------------------- | ------------------------------------------------------------------- |
| **design-system-patterns**    | Build scalable design systems with tokens, components, and theming  |
| **accessibility-compliance**  | Implement WCAG 2.1/2.2 compliance with proper ARIA and keyboard nav |
| **responsive-design**         | Create fluid layouts with CSS Grid, Flexbox, and container queries  |
| **mobile-ios-design**         | Design iOS apps following Human Interface Guidelines                |
| **mobile-android-design**     | Design Android apps following Material Design 3 guidelines          |
| **react-native-design**       | Cross-platform design patterns for React Native applications        |
| **web-component-design**      | Build accessible, reusable web components with Shadow DOM           |
| **interaction-design**        | Create micro-interactions, animations, and gesture-based interfaces |
| **visual-design-foundations** | Apply typography, color theory, spacing, and visual hierarchy       |

### Game Development (2 skills)

| Skill                       | Description                                                          |
| --------------------------- | -------------------------------------------------------------------- |
| **unity-ecs-patterns**      | Implement Unity ECS for high-performance game systems                |
| **godot-gdscript-patterns** | Build Godot games with GDScript best practices and scene composition |

### HR Legal Compliance (2 skills)

| Skill                             | Description                                                      |
| --------------------------------- | ---------------------------------------------------------------- |
| **gdpr-data-handling**            | Implement GDPR-compliant data processing with consent management |
| **employment-contract-templates** | Generate employment contracts with jurisdiction-specific clauses |

### Incident Response (3 skills)

| Skill                          | Description                                                           |
| ------------------------------ | --------------------------------------------------------------------- |
| **postmortem-writing**         | Write blameless postmortems with root cause analysis and action items |
| **incident-runbook-templates** | Create runbooks for common incident scenarios with escalation paths   |
| **on-call-handoff-patterns**   | Design on-call handoffs with context preservation and alert routing   |

### Quantitative Trading (2 skills)

| Skill                        | Description                                                             |
| ---------------------------- | ----------------------------------------------------------------------- |
| **backtesting-frameworks**   | Build backtesting systems with realistic slippage and transaction costs |
| **risk-metrics-calculation** | Calculate VaR, Sharpe ratio, and drawdown metrics for portfolios        |

### Systems Programming (3 skills)

| Skill                       | Description                                                                 |
| --------------------------- | --------------------------------------------------------------------------- |
| **rust-async-patterns**     | Implement async Rust with Tokio, futures, and proper error handling         |
| **go-concurrency-patterns** | Design Go concurrency with channels, worker pools, and context cancellation |
| **memory-safety-patterns**  | Write memory-safe code with ownership, bounds checking, and sanitizers      |

### Conductor - Project Management (3 skills)

| Skill                          | Description                                                                                             |
| ------------------------------ | ------------------------------------------------------------------------------------------------------- |
| **context-driven-development** | Apply Context-Driven Development methodology with product context, specifications, and phased planning  |
| **track-management**           | Manage development tracks for features, bugs, chores, and refactors with specs and implementation plans |
| **workflow-patterns**          | Implement TDD workflows, commit strategies, and verification checkpoints for systematic development     |

### Agent Teams (6 skills)

| Skill                              | Description                                                                                            |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **multi-reviewer-patterns**        | Coordinate parallel code reviews across quality dimensions with deduplication and severity calibration |
| **parallel-debugging**             | Debug complex issues using competing hypotheses, parallel investigation, and root-cause arbitration    |
| **parallel-feature-development**   | Coordinate parallel feature work with file ownership, conflict avoidance, and integration patterns    |
| **task-coordination-strategies**   | Decompose complex tasks, design dependency graphs, and balance workload across multi-agent teams      |
| **team-communication-protocols**   | Structured messaging for agent teams: message types, plan approval, and shutdown procedures           |
| **team-composition-patterns**      | Design optimal team compositions with sizing heuristics, presets, and agent type selection            |

### Reverse Engineering (4 skills)

| Skill                              | Description                                                                                          |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **anti-reversing-techniques**      | Understand anti-reversing, obfuscation, and protection techniques encountered during analysis        |
| **binary-analysis-patterns**       | Disassembly, decompilation, control flow analysis, and code pattern recognition                      |
| **memory-forensics**               | Memory acquisition, process analysis, and artifact extraction using Volatility and related tools     |
| **protocol-reverse-engineering**   | Network protocol reverse engineering including packet analysis and custom protocol documentation     |

### Startup Business Analyst (5 skills)

| Skill                              | Description                                                                                          |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **competitive-landscape**          | Competitive analysis, differentiation, and positioning using Porter's Five Forces and related models |
| **market-sizing-analysis**         | TAM/SAM/SOM calculations using top-down, bottom-up, and value-theory methodologies                   |
| **startup-financial-modeling**     | 3–5 year financial models with revenue, costs, cash flow, and scenario planning                      |
| **startup-metrics-framework**      | Track and optimize key SaaS, marketplace, consumer, and B2B startup metrics from seed to Series A    |
| **team-composition-analysis**      | Hiring plans, org structures, compensation, and equity allocation for early-stage startups           |

### Shell Scripting (3 skills)

| Skill                          | Description                                                                                  |
| ------------------------------ | -------------------------------------------------------------------------------------------- |
| **bash-defensive-patterns**    | Defensive Bash programming techniques for production-grade scripts                          |
| **bats-testing-patterns**      | Bash Automated Testing System (Bats) for comprehensive shell script testing                 |
| **shellcheck-configuration**   | ShellCheck static analysis configuration and usage for shell script quality                 |

### Database Design (1 skill)

| Skill                         | Description                                                       |
| ----------------------------- | ----------------------------------------------------------------- |
| **postgresql-table-design**   | Design and review PostgreSQL-specific schemas with proper modeling |

### Documentation Standards (1 skill)

| Skill    | Description                                                                                   |
| -------- | --------------------------------------------------------------------------------------------- |
| **hads** | HADS (Human-AI Document Standard) — semantic Markdown tagging for token-efficient AI reading |

### .NET Contribution (1 skill)

| Skill                          | Description                                                                       |
| ------------------------------ | --------------------------------------------------------------------------------- |
| **dotnet-backend-patterns**    | C#/.NET backend patterns for robust APIs, MCP servers, and enterprise applications |

### Plugin Eval (1 skill)

| Skill                       | Description                                                                                |
| --------------------------- | ------------------------------------------------------------------------------------------ |
| **evaluation-methodology**  | PluginEval quality methodology — dimensions, rubrics, statistical methods, scoring formulas |

### Block No-Verify (1 skill)

| Skill                      | Description                                                                                      |
| -------------------------- | ------------------------------------------------------------------------------------------------ |
| **block-no-verify-hook**   | PreToolUse hook preventing AI agents from skipping git pre-commit hooks via bypass flags         |

### Protect MCP (1 skill)

| Skill                  | Description                                                                                                                  |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **protect-mcp-setup**  | Configure Cedar policy enforcement and Ed25519 signed receipts for tool calls; example policies for research/dev/production  |

### Social Publishing (1 skill)

| Skill                  | Description                                                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **social-publishing**  | Schedule and publish social media posts across 13 platforms via the SocialClaw API                                       |

### AI & Agent Orchestration (5 skills)

| Skill | Description |
| ----- | ----------- |
| **context-manager** | Orchestrate dynamic context, vector DB, and knowledge graph management |
| **multi-agent-optimize** | Profile and optimize multi-agent performance and costs |
| **improve-agent** | Improve agent prompts with A/B testing and refinement |
| **context-save** | Capture and preserve project state and knowledge for multi-session workflows |
| **context-restore** | Restore prior session context from semantic retrieval |

### Architecture & Documentation (9 skills)

| Skill | Description |
| ----- | ----------- |
| **c4-context** | Generate C4 system context diagrams with personas and user journeys |
| **c4-container** | Map deployment containers with API documentation |
| **c4-component** | Synthesize logical component relationships |
| **c4-code** | Analyze code-level directory structure |
| **docs-architect** | Generate long-form technical manuals and ebooks |
| **tutorial-engineer** | Create interactive tutorial content |
| **doc-generate** | Automate documentation generation from code |
| **code-explain** | Explain code structure and logic |

### API & Backend Security (4 skills)

| Skill | Description |
| ----- | ----------- |
| **api-documenter** | Create OpenAPI 3.1 specs, mock servers, and developer portals |
| **api-mock** | Build mock servers with stubbing, scenarios, and contract testing |
| **backend-security-coder** | Implement secure coding, input validation, and authentication |
| **backend-architect** | Design APIs, microservices, and distributed systems |

### Brand & Design (1 skill)

| Skill | Description |
| ----- | ----------- |
| **brand-landingpage** | Run brand discovery interviews and generate deployment-ready landing pages |

### Code Quality & Maintenance (4 skills)

| Skill | Description |
| ----- | ----------- |
| **legacy-modernizer** | Modernize legacy code to current standards and patterns |
| **refactor-clean** | Refactor code with automated analysis and clean code principles |
| **tech-debt** | Identify, prioritize, and pay down technical debt |
| **deps-audit** | Audit dependencies for vulnerabilities, licenses, and supply chain risks |

### Code Review & Governance (7 skills)

| Skill | Description |
| ----- | ----------- |
| **architect-review** | Conduct architecture and design pattern reviews |
| **review-policy-author** | Author Cedar policies for AI agent review governance |
| **approve-review** | Manage approval windows for AI-assisted code reviews |
| **list-pending** | List denied actions in review governance workflow |
| **pr-enhance** | Enhance pull requests with automated quality analysis |
| **git-workflow** | Orchestrate full git workflow from branch creation to merge |
| **onboard** | Onboard new contributors to standardized git workflows |

### Content & SEO Marketing (12 skills)

| Skill | Description |
| ----- | ----------- |
| **content-marketer** | Create and distribute multi-channel content marketing strategies |
| **search-specialist** | Optimize content for SEO and search marketing |
| **seo-content-refresher** | Update outdated statistics, dates, and examples in existing content |
| **seo-cannibalization-detector** | Identify and resolve keyword conflicts across content |
| **seo-authority-builder** | Build link authority and domain trust |
| **seo-content-writer** | Write SEO-optimized content based on keyword research |
| **seo-content-planner** | Plan editorial calendars and topical content strategy |
| **seo-content-auditor** | Audit existing content for SEO gaps and opportunities |
| **seo-structure-architect** | Design header hierarchy, schema markup, and site architecture |
| **seo-snippet-hunter** | Target featured snippets and rich search results |
| **seo-meta-optimizer** | Optimize meta titles, descriptions, and tags |
| **seo-keyword-strategist** | Develop comprehensive keyword targeting strategies |

### Customer & Sales Automation (2 skills)

| Skill | Description |
| ----- | ----------- |
| **sales-automator** | Automate sales email sequences, cadences, and proposal generation |
| **customer-support** | Automate customer support responses and triage workflows |

### Database Operations (6 skills)

| Skill | Description |
| ----- | ----------- |
| **database-optimizer** | Optimize database queries, indexes, and schema performance |
| **database-admin** | Manage database administration, backups, and operations |
| **sql-migrations** | Execute zero-downtime SQL migrations (expand-contract, blue-green) |
| **migration-observability** | Monitor migration progress, health, and rollback status |
| **cost-optimize** | Analyze and reduce cloud database infrastructure costs |

### Debugging & Error Handling (9 skills)

| Skill | Description |
| ----- | ----------- |
| **debugger** | Perform systematic root cause analysis of software failures |
| **dx-optimizer** | Optimize developer debugging workflows and tooling configurations |
| **smart-debug** | AI-assisted triage, diagnosis, and fix suggestions |
| **error-detective** | Analyze log files, error patterns, and exception traces |
| **devops-troubleshooter** | Debug infrastructure, CI/CD, and deployment issues |
| **debug-trace** | Set up distributed tracing and observability pipelines for debugging |
| **error-analysis** | Classify, categorize, and prioritize error patterns |
| **error-trace** | Trace errors end-to-end through distributed systems |
| **multi-agent-review** | Coordinate multi-agent debugging investigations in parallel |

### Deployment & DevOps (3 skills)

| Skill | Description |
| ----- | ----------- |
| **deployment-engineer** | Design CI/CD pipelines, GitOps workflows, and progressive delivery |
| **terraform-specialist** | Manage infrastructure as code with Terraform and OpenTofu |
| **config-validate** | Validate configuration schemas and environment consistency |

### Full-Stack Development (4 skills)

| Skill | Description |
| ----- | ----------- |
| **test-automator** | Automate testing across the full application stack |
| **security-auditor** | Audit full-stack security posture and vulnerability surface |
| **performance-engineer** | Optimize end-to-end application performance |
| **deployment-engineer** | Manage full-stack deployment and release processes |

### Generative AI & Media (5 skills)

| Skill | Description |
| ----- | ----------- |
| **prompt-crafter** | Engineer prompts for AI image and media generation |
| **image-generator** | Execute AI image generation workflows with multi-direction output |
| **gallery-researcher** | Search and curate AI art inspiration from 1,300+ curated library |
| **model-advisor** | Recommend optimal AI models from 130+ across 18 providers |
| **task-executor** | Manage and execute media generation tasks across providers |

### Language & Platform Development (13 skills)

| Skill | Description |
| ----- | ----------- |
| **arm-cortex-expert** | Develop embedded firmware for ARM Cortex-M microcontrollers |
| **haskell-pro** | Build functional programs with advanced type systems and purity |
| **elixir-pro** | Build Elixir/OTP concurrent and fault-tolerant systems |
| **julia-pro** | Write performant Julia code for scientific and numerical computing |
| **java-pro** | Build Java 21+ applications with Spring Boot and modern patterns |
| **scala-pro** | Develop Scala applications with functional and object-oriented paradigms |
| **csharp-pro** | Develop C#/.NET applications with modern language features |
| **ui-ux-designer** | Design cross-platform user interfaces and experiences |
| **mobile-developer** | Build cross-platform mobile applications |
| **ios-developer** | Build native iOS applications with Swift and SwiftUI |
| **flutter-expert** | Build Flutter applications with Dart and Material Design |
| **ruby-pro** | Develop Ruby applications with Rails and best practices |
| **php-pro** | Develop PHP applications with modern frameworks |

### Performance & Observability (3 skills)

| Skill | Description |
| ----- | ----------- |
| **performance-engineer** | Profile, load test, and optimize application performance end-to-end |
| **observability-engineer** | Set up comprehensive monitoring, logging, and distributed tracing |
| **frontend-developer** | Optimize React and Next.js frontend performance and Core Web Vitals |

### Product Delivery (7 skills)

| Skill | Description |
| ----- | ----------- |
| **orchestrate** | Generate product specs and orchestrate the full delivery pipeline |
| **architect** | Create technical designs and architecture for features |
| **implement** | Write production-ready code following best practices |
| **qa** | Perform quality assurance testing and validation |
| **review** | Conduct thorough code reviews for quality and correctness |
| **playwright** | Write and maintain E2E tests with Playwright |
| **scan** | Analyze codebase structure for project documentation generation |

### Security, Compliance & Audit (5 skills)

| Skill | Description |
| ----- | ----------- |
| **frontend-security-coder** | Secure React, Vue, and Angular apps against XSS and web vulnerabilities |
| **mobile-security-coder** | Secure mobile applications against platform-specific threats |
| **xss-scan** | Scan for cross-site scripting vulnerabilities across codebases |
| **compliance-check** | Run regulatory compliance audits (GDPR, HIPAA, SOC2, PCI-DSS) |
| **signed-audit-trails-recipe** | Set up Ed25519 signed audit trails with JCS and hash chains |

### Testing & QA (7 skills)

| Skill | Description |
| ----- | ----------- |
| **tdd-orchestrator** | Orchestrate red-green-refactor TDD cycles with discipline |
| **tdd-red** | Write failing tests first to define expected behavior |
| **tdd-green** | Make tests pass with minimal implementation code |
| **tdd-refactor** | Clean up and optimize code after green phase |
| **test-generate** | Automatically generate comprehensive unit tests |
| **test-automator** | Automate test execution, maintenance, and reporting |

### Team & Workflow (3 skills)

| Skill | Description |
| ----- | ----------- |
| **dx-optimizer** | Improve developer tooling, workflows, and productivity |
| **standup-notes** | Generate async standup notes from commits, PRs, and Jira activity |
| **issue** | Manage development issues, tickets, and task tracking |

### Utilities & Tools (1 skill)

| Skill | Description |
| ----- | ----------- |
| **file-conversion** | Convert files between 999+ formats via the ChangeThisFile API |

## How Skills Work

### Activation

Skills are automatically activated when Claude detects matching patterns in your request:

```
User: "Set up Kubernetes deployment with Helm chart"
→ Activates: helm-chart-scaffolding, k8s-manifest-generator

User: "Build a RAG system for document Q&A"
→ Activates: rag-implementation, prompt-engineering-patterns

User: "Optimize Python async performance"
→ Activates: async-python-patterns, python-performance-optimization
```

### Progressive Disclosure

Skills use a three-tier architecture for token efficiency:

1. **Metadata** (Frontmatter): Name and activation criteria (always loaded)
2. **Instructions**: Core guidance and patterns (loaded when activated)
3. **Resources**: Examples and templates (loaded on demand)

### Integration with Agents

Skills work alongside agents to provide deep domain expertise:

- **Agents**: High-level reasoning and orchestration
- **Skills**: Specialized knowledge and implementation patterns

Example workflow:

```
backend-architect agent → Plans API architecture
  ↓
api-design-principles skill → Provides REST/GraphQL best practices
  ↓
fastapi-templates skill → Supplies production-ready templates
```

## Specification Compliance

All 300+ skills follow the [Agent Skills Specification](https://agentskills.io/specification):

- ✓ Required `name` field (hyphen-case)
- ✓ Required `description` field with "Use when" clause
- ✓ Descriptions under 1024 characters
- ✓ Complete, non-truncated descriptions
- ✓ Proper YAML frontmatter formatting

## Creating New Skills

To add a skill to a plugin:

1. Create `plugins/{plugin-name}/skills/{skill-name}/SKILL.md`
2. Add YAML frontmatter:

   ```yaml
   ---
   name: skill-name
   description: What the skill does. Use when [activation trigger].
   ---
   ```

3. Write comprehensive skill content using progressive disclosure
4. Add skill path to `marketplace.json`:

   ```json
   {
     "name": "plugin-name",
     "skills": ["./skills/skill-name"]
   }
   ```

### Skill Structure

```
plugins/{plugin-name}/
└── skills/
    └── {skill-name}/
        └── SKILL.md        # Frontmatter + content
```

## Benefits

- **Token Efficiency**: Load only relevant knowledge when needed
- **Specialized Expertise**: Deep domain knowledge without bloat
- **Clear Activation**: Explicit triggers prevent unwanted invocation
- **Composability**: Mix and match skills across workflows
- **Maintainability**: Isolated updates don't affect other skills

## Resources

- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [Agent Skills Documentation](https://docs.claude.com/en/docs/claude-code/skills)
