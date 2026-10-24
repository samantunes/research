#!/usr/bin/env python3
"""End-to-End WebSocket & Hybrid Search Validation for Enki Research Engine (GPT Researcher)."""

import asyncio
import json
import os
import sys
import time
import websockets

WS_URL = "ws://127.0.0.1:8000/ws"
OUTPUTS_DIR = "/opt/enki-research/outputs"

PAYLOAD = {
    "task": "Compare abordagens de grafos de conhecimento (Knowledge Graphs) vs RAG vetorial tradicional para sistemas CAD/BIM em engenharia elétrica",
    "report_type": "research_report",
    "report_source": "web",
    "tone": "Objective",
}


async def run_test():
    print(f"[INFO] Conectando ao WebSocket: {WS_URL}")
    start_time = time.time()

    subqueries_generated = False
    tavily_or_web_urls = []
    arxiv_urls = []
    scraping_triggered = False
    report_chunks = []
    saved_paths = None
    errors = []

    async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=120, max_size=10 * 1024 * 1024) as ws:
        command = f"start {json.dumps(PAYLOAD, ensure_ascii=False)}"
        print(f"[INFO] Enviando comando: {command[:120]}...")
        await ws.send(command)

        while True:
            try:
                raw_msg = await asyncio.wait_for(ws.recv(), timeout=300)
            except asyncio.TimeoutError:
                errors.append("Timeout aguardando mensagem do WebSocket (300s)")
                break

            if raw_msg == "pong":
                continue

            try:
                data = json.loads(raw_msg)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")
            content = data.get("content", "")
            output = str(data.get("output", ""))
            metadata = data.get("metadata", None)

            if msg_type == "logs":
                clean_out = output.strip().replace("\n", " ")
                print(f"[{time.time() - start_time:6.1f}s] [LOG:{content}] {clean_out[:180]}")

                if content == "subqueries" or "sub_queries" in content or "plan_research" in content or "Thinking" in output or "queries" in clean_out.lower():
                    subqueries_generated = True
                    if metadata and isinstance(metadata, list):
                        print(f"   -> Sub-queries geradas ({len(metadata)}): {metadata}")

                if content == "added_source_url" or "http" in output:
                    url_candidate = metadata if isinstance(metadata, str) and metadata.startswith("http") else output
                    if "arxiv.org" in url_candidate.lower():
                        arxiv_urls.append(url_candidate)
                    elif "http" in url_candidate.lower():
                        tavily_or_web_urls.append(url_candidate)

                if content in ("scraping_content", "researching", "fetching_query_content") or "scrap" in clean_out.lower():
                    scraping_triggered = True

                if "OPENAI_API_KEY" in output or content == "error":
                    errors.append(f"Erro detectado no log: {output}")

            elif msg_type == "report":
                report_chunks.append(output)

            elif msg_type == "path":
                saved_paths = data.get("output", {})
                print(f"[{time.time() - start_time:6.1f}s] [PATH] Arquivos salvos: {json.dumps(saved_paths, indent=2)}")
                break

            elif msg_type == "error":
                errors.append(f"WebSocket error message: {output}")
                print(f"[ERROR] {output}")
                break

    full_report = "".join(report_chunks)
    print("\n" + "=" * 70)
    print("RESUMO DA VALIDAÇÃO E2E")
    print("=" * 70)
    print(f"1. Tempo total de execução: {time.time() - start_time:.1f}s")
    print(f"2. Sub-perguntas geradas (STRATEGIC_LLM DeepSeek): {subqueries_generated}")
    print(f"3. Eventos de URLs Web/Tavily capturados: {len(tavily_or_web_urls)}")
    print(f"4. Eventos de URLs ArXiv capturados: {len(arxiv_urls)}")
    print(f"5. Etapa de Scraping/Embeddings executada: {scraping_triggered}")
    print(f"6. Tamanho do relatório recebido via stream: {len(full_report)} caracteres")
    print(f"7. Caminhos de saída retornados: {saved_paths}")
    print(f"8. Erros de runtime/OPENAI_API_KEY: {len(errors)} -> {errors}")

    if not saved_paths or "md" not in saved_paths:
        print("[FAIL] Relatório Markdown não retornou caminho salvo!")
        sys.exit(1)

    md_rel_path = saved_paths["md"]
    md_abs_path = os.path.join("/opt/enki-research", md_rel_path) if not os.path.isabs(md_rel_path) else md_rel_path
    if os.path.exists(md_abs_path):
        size = os.path.getsize(md_abs_path)
        print(f"[PASS] Arquivo Markdown verificado no disco: {md_abs_path} ({size} bytes)")
    else:
        print(f"[FAIL] Arquivo Markdown não encontrado em {md_abs_path}")
        sys.exit(1)

    if errors:
        print("[FAIL] Erros detectados durante a pesquisa!")
        sys.exit(1)

    print("[SUCCESS] Teste End-to-End concluído com 100% de sucesso!")


if __name__ == "__main__":
    asyncio.run(run_test())
