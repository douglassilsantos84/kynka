from __future__ import annotations
import re
from dataclasses import asdict, is_dataclass

WRITE_TOOLS = {"inventory.exit","inventory.entry","material_request.create","purchase_order.create","supplier.update"}
ROLE_TOOLS = {
 "admin":{"*"},
 "stock_manager":{"inventory.list","documents.ask","memory.search","memory.save","workflow.create",
                  "inventory.exit","inventory.entry","material_request.create"},
 "buyer":{"inventory.list","supplier.list","documents.ask","memory.search","memory.save","workflow.create",
          "purchase_order.create","supplier.update"},
 "worker":{"inventory.list","documents.ask","memory.search","memory.save","workflow.create","material_request.create"},
}

def safe(v):
    if is_dataclass(v): return {k:safe(x) for k,x in asdict(v).items()}
    if isinstance(v, dict): return {str(k):safe(x) for k,x in v.items()}
    if isinstance(v, (list, tuple)): return [safe(x) for x in v]
    if hasattr(v, "value") and not isinstance(v, (str,int,float,bool)): return safe(v.value)
    return v if isinstance(v, (str,int,float,bool)) or v is None else str(v)

class AgenticService:
    def __init__(self, store, inventory, suppliers, documents):
        self.store, self.inventory, self.suppliers, self.documents = store, inventory, suppliers, documents

    def allowed(self, identity, tool):
        a = ROLE_TOOLS.get(identity["role"], set())
        return "*" in a or tool in a

    def catalog(self, identity):
        tools = [
          ("inventory.list","operations",False),("supplier.list","procurement",False),
          ("documents.ask","knowledge",False),("memory.search","memory",False),
          ("memory.save","memory",False),("workflow.create","orchestrator",False),
          ("inventory.exit","operations",True),("inventory.entry","operations",True),
          ("material_request.create","operations",True),("purchase_order.create","procurement",True),
          ("supplier.update","procurement",True)]
        return [{"name":n,"agent":a,"mutating":m,"allowed":self.allowed(identity,n),"requires_approval":m}
                for n,a,m in tools]

    def remember(self, identity, content, kind="fact", scope="user", importance=.5, metadata=None):
        if scope == "organization" and identity["role"] != "admin":
            raise PermissionError("Apenas administradores podem criar memoria organizacional.")
        return {"id": self.store.add_memory(identity["organization_id"], identity["id"], content,
                                             kind, scope, importance, metadata), "stored": True}

    def recall(self, identity, query, limit=8):
        terms, scored = set(self._terms(query)), []
        for r in self.store.memories(identity["organization_id"], identity["id"], 200):
            overlap = len(terms & set(self._terms(r["content"])))
            score = overlap * 2 + float(r["importance"])
            if overlap or not terms:
                scored.append((score, r))
        return [r for _,r in sorted(scored, key=lambda x:(x[0],x[1]["id"]), reverse=True)[:limit]]

    def run(self, identity, objective, document_ids=None):
        agent = self._agent(objective)
        rid = self.store.create_run(identity["organization_id"], identity["id"], agent, objective)
        low = objective.lower()
        try:
            mem = self.recall(identity, objective, 5)
            if any(k in low for k in ("document","contrato","manual","fatura","cotacao","cotação","pdf","proposta")):
                if not self.allowed(identity, "documents.ask"): raise PermissionError("Perfil sem acesso a documentos.")
                result = {"run_id":rid,"agent":"knowledge","mode":"grounded-rag","memory_context":mem,
                          "answer":safe(self.documents.ask(objective, document_ids=document_ids, limit=6))}
            elif any(k in low for k in ("estoque","inventario","inventário","material","disjuntor","cabo")) and not any(k in low for k in ("comprar","compra","fornecedor","preco","preço")):
                if not self.allowed(identity, "inventory.list"): raise PermissionError("Perfil sem acesso ao inventario.")
                result = {"run_id":rid,"agent":"operations","mode":"tool","tool":"inventory.list",
                          "memory_context":mem,"data":safe(self.inventory.list_materials())}
            elif any(k in low for k in ("fornecedor","comprar","compra","preco","preço","prazo")):
                if not self.allowed(identity, "supplier.list"): raise PermissionError("Perfil sem acesso a fornecedores.")
                result = {"run_id":rid,"agent":"procurement","mode":"tool","tool":"supplier.list",
                          "memory_context":mem,"data":safe(self.suppliers.list_suppliers())}
            else:
                result = {"run_id":rid,"agent":"orchestrator","mode":"plan",
                          "memory_context":mem,"plan":self.plan(identity, objective)}
            self.store.finish_run(rid, "completed", result)
            return result
        except Exception as e:
            self.store.finish_run(rid, "failed", error=str(e))
            raise

    def plan(self, identity, objective):
        low, steps = objective.lower(), []
        if any(k in low for k in ("document","contrato","manual","fatura","cotacao","cotação")):
            steps.append({"agent_name":"knowledge","tool_name":"documents.ask","arguments":{"question":objective},"requires_approval":False})
        if any(k in low for k in ("estoque","material","inventario","inventário")):
            steps.append({"agent_name":"operations","tool_name":"inventory.list","arguments":{},"requires_approval":False})
        if any(k in low for k in ("fornecedor","compra","comprar","preco","preço")):
            steps.append({"agent_name":"procurement","tool_name":"supplier.list","arguments":{},"requires_approval":False})
        if any(k in low for k in ("crie","criar","registre","registar","comprar","dar baixa","saida","saída","alterar","atualizar")):
            tool = "material_request.create" if "solicita" in low or "material" in low else "purchase_order.create" if "compra" in low else "inventory.exit"
            if not self.allowed(identity, tool): raise PermissionError("Ferramenta nao autorizada: " + tool)
            steps.append({"agent_name":"procurement" if tool.startswith("purchase") else "operations",
                          "tool_name":tool,"arguments":{"objective":objective},"requires_approval":True})
        if not steps:
            steps = [{"agent_name":"orchestrator","tool_name":"memory.search","arguments":{"query":objective},"requires_approval":False}]
        for s in steps:
            if not self.allowed(identity, s["tool_name"]):
                raise PermissionError("Ferramenta nao autorizada: " + s["tool_name"])
        return {"objective":objective,"steps":steps,"requires_approval":any(s["requires_approval"] for s in steps)}

    def create_workflow(self, identity, title, objective):
        return self.store.create_workflow(identity["organization_id"], identity["id"], title,
                                          objective, self.plan(identity, objective)["steps"])

    def approve(self, identity, wid):
        if identity["role"] not in {"admin","stock_manager","buyer"}:
            raise PermissionError("Perfil sem permissao para aprovar workflows.")
        if not self.store.approve(wid, identity["organization_id"], identity["id"]):
            raise ValueError("Workflow inexistente ou nao aguarda aprovacao.")
        return self.store.workflow(wid, identity["organization_id"])

    def execute(self, identity, wid):
        w = self.store.workflow(wid, identity["organization_id"])
        if not w: raise ValueError("Workflow nao encontrado.")
        if w["status"] == "awaiting_approval": raise PermissionError("Workflow aguarda aprovacao humana.")
        if w["status"] != "ready": raise ValueError("Workflow nao executavel no estado " + w["status"])
        self.store.set_workflow_status(wid, identity["organization_id"], "running")
        failed = False
        for step in w["steps"]:
            tool = step["tool_name"]
            if tool in WRITE_TOOLS:
                self.store.set_step(step["id"], "blocked",
                                    error="Mutacao automatica bloqueada ate executor transacional de producao.")
                failed = True
                break
            try:
                if tool == "inventory.list": res = safe(self.inventory.list_materials())
                elif tool == "supplier.list": res = safe(self.suppliers.list_suppliers())
                elif tool == "documents.ask": res = safe(self.documents.ask(step["arguments"].get("question") or w["objective"], limit=6))
                else: res = self.recall(identity, step["arguments"].get("query") or w["objective"])
                self.store.set_step(step["id"], "completed", res)
            except Exception as e:
                self.store.set_step(step["id"], "failed", error=str(e))
                failed = True
                break
        self.store.set_workflow_status(wid, identity["organization_id"], "failed" if failed else "completed")
        return self.store.workflow(wid, identity["organization_id"])

    @staticmethod
    def _agent(text):
        low = text.lower()
        if any(k in low for k in ("document","contrato","manual","fatura","cotacao","cotação")): return "knowledge"
        if any(k in low for k in ("fornecedor","compra","preco","preço")): return "procurement"
        if any(k in low for k in ("estoque","material","obra","inventario","inventário")): return "operations"
        return "orchestrator"

    @staticmethod
    def _terms(text):
        return re.findall(r"[a-zA-ZÀ-ÿ0-9_-]{2,}", text.lower())
