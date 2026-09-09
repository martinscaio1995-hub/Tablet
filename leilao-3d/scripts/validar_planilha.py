import formulas, warnings, math
warnings.filterwarnings("ignore")
xl = formulas.ExcelModel().loads("leilao-3d/custo-lance-minimo.xlsx").finish()
sol = xl.calculate()

def g(key):
    for k, v in sol.items():
        if k.upper().endswith(key.upper()):
            try:
                return v.value[0, 0]
            except Exception:
                return v
    return "<missing>"

F = "'[CUSTO-LANCE-MINIMO.XLSX]CUSTO POR PECA'!"
V = "'[CUSTO-LANCE-MINIMO.XLSX]REGISTRO DE VENDAS'!"

# premissas
prem = {c: g(F + c) for c in ["B5","B6","B7","B8","B9","B10","B11","B12","B13"]}
print("PREMISSAS:", prem)

row = 17  # linha do exemplo
cells = ["E","F","G","H","I","J","K","L","M","N","O","P"]
got = {c: g(F + c + str(row)) for c in cells}
print("\nLINHA EXEMPLO (95 g, 5.5 h, 8 min):")
for c in cells:
    print(f"  {c}{row} = {got[c]}")

# recalculo independente, na mão
kg, kwh, w, emb, falha, desg, com, hora, mult = (110.0,0.95,100.0,4.0,0.10,0.50,0.08,25.0,3.0)
g_, h_, m_ = 95, 5.5, 8
E = g_*kg/1000; F_ = h_*w/1000*kwh; G = emb; H = h_*desg; I = m_/60*hora
J = E+F_+G+H+I; K = J*falha; L = J+K
M = math.ceil(L/(1-com)); N = math.ceil(L*mult/(1-com)); O = N*(1-com)-L; P = O/N
exp = dict(zip(cells,[E,F_,G,H,I,J,K,L,M,N,O,P]))
print("\nCONFERENCIA:")
ok = True
for c in cells:
    a, b = got[c], exp[c]
    good = isinstance(a,(int,float)) and abs(a-b) < 0.005
    ok &= good
    print(f"  {c}: planilha={a!r:>22}  esperado={round(b,4)!r:>10}  {'OK' if good else 'DIVERGENTE'}")

# aba de vendas: custo puxado por INDEX/MATCH
print("\nREGISTRO DE VENDAS (linha 5):")
for c in ["D","E","F","H"]:
    print(f"  {c}5 = {g(V+c+'5')}")
print("\nTOTAIS:", {c: g(V+c+"67") for c in ["D","E","F","G","H"]})
print("\nRESULTADO:", "TODAS AS FORMULAS CONFEREM" if ok else "HA DIVERGENCIA")
