"""El indicador de TradingView traducido a Python, paso a paso, para comprobar que decide igual que el bot
(tests/test_tradingview.py). Si cambiáis plantilla.pine, cambiad esto igual; si cambian las reglas de crt/, las dos cosas.

Las velas semanales y mensuales se llevan como las de TradingView: el estado de la última vela cerrada.
"""
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta

EPOCA = date(1970, 1, 1)

@dataclass
class V:
    t: datetime; o: float; h: float; l: float; c: float; iIni: int; iFin: int

@dataclass
class Ev:
    id: int; rango: bool; dir: int; iFormado: int; iVelaIni: int
    objetivo: float = None; barrido: float = None; escenario: str = "otro"; vela1Rel: float = None
    estado: int = 0; velasDesde: int = 0; velasHastaCompletar: int = -1

@dataclass
class Marco:
    nombre: str; codigo: int; cerradas: list = field(default_factory=list); parcial: V = None
    clave: int = -1; ultimo: Ev = None; barridoAlc: int = -1; barridoBaj: int = -1

@dataclass
class S:
    idea1: int; idea2: int; dir: int; barrido: float; objetivo: float; iInicio: int; via: str; escenario: str; vela1Rel: float

class Espejo:
    def __init__(self, dif, col, ratio=2.0, espera=45, desdeM=60, hastaM=780, maxOps=2, topeR=3.0, inicio4h=17,
                 comprobar=True, sin1h=False, sinVeto=False, backtest=False):
        self.__dict__.update(locals()); del self.__dict__["self"]
        if backtest: self.maxOps = 3
        self.cont = 0
        self.h1, self.h3, self.h4, self.d1 = Marco("H1", 1), Marco("H3", 2), Marco("H4", 3), Marco("D1", 4)
        self.wU = self.mU = None
        self.op = None; self.anterior = None; self.usados = []; self.vistos = []; self.rDia = {}; self.opsDia = {}
        self.kWPrev = 0; self.diaPrev = 0; self.cierrePrev = None
        self.ops = []; self.senales = []
        # semanal y mensual "de TradingView": velas cerradas
        self.htf = {"W": dict(vela=None, clave=None, prev=None, prev2=None, st=self._st0()), "M": dict(vela=None, clave=None, prev=None, prev2=None, st=self._st0())}
        self.wPrev = self.mPrev = None

    @staticmethod
    def _st0():
        return dict(uRango=False, uDir=0, uObj=None, uBarr=None, uEstado=-1, uId=0)

    # ── rangos
    def evaluar(self, v1, v2):
        tomaMin, tomaMax = v2.l < v1.l, v2.h > v1.h
        if v2.c > v1.h: return Ev(0, False, 1, v2.iFin, v2.iIni)
        if v2.c < v1.l: return Ev(0, False, -1, v2.iFin, v2.iIni)
        if tomaMin and not tomaMax: return Ev(0, True, 1, v2.iFin, v2.iIni, v1.h, v2.l)
        if tomaMax and not tomaMin: return Ev(0, True, -1, v2.iFin, v2.iIni, v1.l, v2.h)
        return None
    @staticmethod
    def semaforo(u, d):
        if u is None: return "ambar"
        if not u.rango: return "rojo" if u.dir != d else "ambar"
        if u.estado == 0: return "verde" if u.dir == d else "rojo"
        return "ambar"
    @staticmethod
    def escenario(p, d):
        if p is not None and p.rango and p.dir != d:
            if p.estado == 0: return "3"
            if p.estado == 1: return "2" if p.velasHastaCompletar == 1 else "1"
        return "otro"
    @staticmethod
    def direccion(u):
        if u is None: return 0
        if not u.rango: return u.dir
        return u.dir if u.estado == 0 else 0
    @staticmethod
    def completar(u, b):
        if u is not None and u.rango and u.estado == 0 and u.iFormado < b.iFin:
            if (u.dir > 0 and b.h >= u.objetivo) or (u.dir < 0 and b.l <= u.objetivo):
                u.estado = 1; u.velasHastaCompletar = u.velasDesde + 1
    # ── claves (f_claves) con el reloj de Nueva York
    def claves(self, t):
        h = t.hour
        dia0 = (t.date() - EPOCA).days
        dia = dia0 + (1 if h >= 17 else 0)
        hT = (h + 7) % 24
        k1 = dia * 24 + hT
        k3 = dia * 8 + hT // 3
        h4t = h + 24 - self.inicio4h
        k4 = (dia0 + (1 if h4t >= 24 else 0)) * 6 + (h4t % 24) // 4
        wd = (dia + 3) % 7
        kW = dia - wd
        return dia, wd, k1, k3, k4, kW
    # ── marcos
    @staticmethod
    def rangoMedio(m):
        n = len(m.cerradas); k = min(n, 20)
        if k >= 5: return sum(v.h - v.l for v in m.cerradas[n - k:]) / k
        return None
    def relativo(self, m, v):
        md = self.rangoMedio(m)
        return (v.h - v.l) / md if md else None
    @staticmethod
    def tomando(m, d):
        if m.parcial is not None and m.cerradas:
            p = m.cerradas[-1]
            return m.parcial.h > p.h if d > 0 else m.parcial.l < p.l
        return False
    @staticmethod
    def sumar(m, b, clave):
        if m.parcial is None:
            m.parcial = V(b.t, b.o, b.h, b.l, b.c, b.iIni, b.iFin); m.clave = clave; m.barridoAlc = m.barridoBaj = -1
        else:
            m.parcial.h = max(m.parcial.h, b.h); m.parcial.l = min(m.parcial.l, b.l); m.parcial.c = b.c; m.parcial.iFin = b.iFin
        if m.cerradas:
            p = m.cerradas[-1]
            if m.barridoAlc < 0 and m.parcial.l < p.l: m.barridoAlc = b.iFin
            if m.barridoBaj < 0 and m.parcial.h > p.h: m.barridoBaj = b.iFin
    def cerrar(self, m):
        v = m.parcial; m.parcial = None; u = m.ultimo
        if u is not None and u.rango and u.estado == 0:
            u.velasDesde += 1
            if (u.dir > 0 and v.c < u.barrido) or (u.dir < 0 and v.c > u.barrido): u.estado = 2
        nuevo = None
        if m.cerradas:
            p = m.cerradas[-1]; nuevo = self.evaluar(p, v)
            if nuevo is not None: nuevo.vela1Rel = self.relativo(m, p)
        m.cerradas.append(v)
        if len(m.cerradas) > 21: m.cerradas.pop(0)
        if nuevo is not None:
            self.cont += 1; nuevo.id = self.cont; nuevo.escenario = self.escenario(u, nuevo.dir); m.ultimo = nuevo
    # ── setups
    @staticmethod
    def claveAnt(codigo, iIni, d): return (iIni * 8 + codigo) * 2 + (1 if d > 0 else 0)
    def cerrado(self, m, d):
        u = m.ultimo
        if u is not None and u.rango and u.estado == 0 and u.dir == d:
            return S(-u.id, self.claveAnt(m.codigo, u.iVelaIni, d), d, u.barrido, u.objetivo, u.iFormado, "cierre", u.escenario, u.vela1Rel)
        return None
    def baseAnticipo(self, m, d, precio):
        ib = m.barridoAlc if d > 0 else m.barridoBaj
        if m.parcial is not None and m.cerradas and ib >= 0:
            p = m.cerradas[-1]
            return (p.l < precio < p.h and not self.tomando(m, d)), ib
        return False, ib
    def hacerAnticipo(self, m, d, iInicio):
        p = m.cerradas[-1]
        return S(self.claveAnt(m.codigo, m.parcial.iIni, d), 0, d, m.parcial.l if d > 0 else m.parcial.h, p.h if d > 0 else p.l, iInicio, "anticipo", self.escenario(m.ultimo, d), self.relativo(m, p))
    def anticipo4h(self, d, precio):
        ok, ib = self.baseAnticipo(self.h4, d, precio)
        if ok:
            if self.sin1h: return self.hacerAnticipo(self.h4, d, ib)
            s1 = self.cerrado(self.h1, d)
            if s1 is not None and s1.iInicio >= ib: return self.hacerAnticipo(self.h4, d, s1.iInicio)
        return None
    def setup4h(self, d, precio):
        return self.cerrado(self.h4, d) or self.anticipo4h(d, precio)
    def anticipoD1(self, d, precio):
        ok, ib = self.baseAnticipo(self.d1, d, precio)
        if ok:
            s4 = self.setup4h(d, precio)
            if s4 is not None and s4.via == "cierre" and s4.iInicio < ib: s4 = self.anticipo4h(d, precio)
            if s4 is not None and s4.iInicio >= ib: return self.hacerAnticipo(self.d1, d, s4.iInicio)
        return None
    def setupD1(self, d, precio):
        return self.cerrado(self.d1, d) or self.anticipoD1(d, precio)
    def colorSimple(self, m, d):
        return "verde" if self.cerrado(m, d) is not None else self.semaforo(m.ultimo, d)
    # ── semanal y mensual: f_crtCerradas sobre velas cerradas
    def htf_paso(self, tf, clave, b):
        """Lleva las velas de TradingView del marco tf y devuelve el estado tras la última cerrada (lookahead + [1])."""
        H = self.htf[tf]
        if H["clave"] is not None and clave != H["clave"]:
            cerrada = H["vela"]; st = H["st"]
            # f_crtCerradas en la barra siguiente: [1] = cerrada, [2] = la anterior
            if st["uEstado"] == 0 and st["uRango"]:
                if (st["uDir"] > 0 and cerrada.h >= st["uObj"]) or (st["uDir"] < 0 and cerrada.l <= st["uObj"]): st["uEstado"] = 1
            if st["uEstado"] == 0 and st["uRango"]:
                if (st["uDir"] > 0 and cerrada.c < st["uBarr"]) or (st["uDir"] < 0 and cerrada.c > st["uBarr"]): st["uEstado"] = 2
            p2 = H["prev"]
            if p2 is not None:
                tomaMin, tomaMax = cerrada.l < p2.l, cerrada.h > p2.h
                nDir, nRango = 0, False
                if cerrada.c > p2.h: nDir = 1
                elif cerrada.c < p2.l: nDir = -1
                elif tomaMin and not tomaMax: nDir, nRango = 1, True
                elif tomaMax and not tomaMin: nDir, nRango = -1, True
                if nDir:
                    st.update(uRango=nRango, uDir=nDir, uObj=(p2.h if nDir > 0 else p2.l) if nRango else None,
                              uBarr=(cerrada.l if nDir > 0 else cerrada.h) if nRango else None, uEstado=0, uId=st["uId"] + 1)
            H["prev"] = cerrada; H["vela"] = None
        if H["vela"] is None:
            H["vela"] = V(b.t, b.o, b.h, b.l, b.c, b.iIni, b.iFin); H["clave"] = clave
        else:
            H["vela"].h = max(H["vela"].h, b.h); H["vela"].l = min(H["vela"].l, b.l); H["vela"].c = b.c
        return dict(H["st"])
    def sesgoBot(self):
        s, m = self.direccion(self.wU), self.direccion(self.mU)
        if s == 0: return m
        if m == -s and not self.sinVeto: return 0
        return s
    # ── niveles, banderas, entradas, salidas
    def niveles(self, d, precio, s):
        if d > 0:
            if precio <= s.barrido: return False, "el precio ya pasó el barrido", None, None, None, None
            entrada = precio + self.dif; stop = s.barrido - self.col; riesgo = entrada - stop
        else:
            if precio >= s.barrido: return False, "el precio ya pasó el barrido", None, None, None, None
            entrada = precio; stop = s.barrido + self.col + self.dif; riesgo = stop - entrada
        if riesgo <= 0 or riesgo < 3 * self.dif: return False, "stop demasiado corto", entrada, stop, riesgo, None
        return True, "", entrada, stop, riesgo, entrada + d * self.ratio * riesgo
    def cabe(self, d, tp, obj):
        if obj is None: return True
        return tp <= obj if d > 0 else tp >= obj + self.dif
    def salir(self, precio, res, dia, t):
        o = self.op; r = (precio - o["entrada"]) / o["riesgo"] * o["dir"]
        self.rDia[dia] = self.rDia.get(dia, 0) + r
        o.update(salida=precio, resultado=res, r=r, t_salida=t); self.ops.append(o); self.op = None
    def mirar(self, b, a, d, dia, mc, tc):
        horario = self.desdeM < mc <= self.hastaM and not (self.espera > 0 and 570 < mc < 570 + self.espera)
        cA, cB = abs(a.c - a.o), abs(b.c - b.o)
        ob = cB > cA and ((a.c < a.o and b.c > b.o and b.c > a.o) if d > 0 else (a.c > a.o and b.c < b.o and b.c < a.o))
        if not (horario and ob): return
        precio = b.c
        usada = lambda i: i != 0 and i in self.usados
        s = self.setup4h(d, precio)
        if s is not None and s.via == "cierre" and (usada(s.idea1) or usada(s.idea2)):
            s = self.anticipo4h(d, precio)
        if s is None or not (b.iFin > s.iInicio) or usada(s.idea1) or usada(s.idea2): return
        sd = self.setupD1(d, precio)
        objetivo = sd.objetivo if (sd is not None and not self.backtest) else None
        diarioVale = self.backtest or sd is not None
        nOk, motivoN, entrada, stop, riesgo, tp = self.niveles(d, precio, s)
        if not self.backtest and self.sesgoBot() != d: dec = "sin sesgo a favor"
        elif not diarioVale: dec = "el diario no está a favor"
        elif self.op is not None: dec = "ya había una operación abierta"
        else:
            self.usados.append(s.idea1)
            if s.idea2 != 0: self.usados.append(s.idea2)
            if self.topeR > 0 and self.rDia.get(dia, 0) <= -self.topeR: dec = "tope de pérdida del día"
            elif self.opsDia.get(dia, 0) >= self.maxOps: dec = "tope de operaciones del día"
            elif not nOk: dec = motivoN
            elif self.comprobar and not self.cabe(d, tp, objetivo): dec = "el TP no cabe antes del objetivo del diario"
            else: dec = "entrada"
        nueva = not (s.idea1 in self.vistos or (s.idea2 != 0 and s.idea2 in self.vistos))
        self.vistos.append(s.idea1)
        if s.idea2 != 0: self.vistos.append(s.idea2)
        if dec == "entrada":
            self.op = dict(dir=d, entrada=entrada, stop=stop, tp=tp, riesgo=riesgo, t=tc)
            self.opsDia[dia] = self.opsDia.get(dia, 0) + 1
        if dec == "entrada" or nueva:
            self.senales.append((tc, d, dec))
    # ── cada barra
    def paso(self, b):
        dia, wd, k1, k3, k4, kW = self.claves(b.t)
        if wd >= 5: return
        # semanal y mensual de TradingView (el valor que vería esta barra)
        w = self.htf_paso("W", kW, b)
        msDia = EPOCA + timedelta(days=dia)
        m = self.htf_paso("M", msDia.year * 12 + msDia.month, b)
        wk = (w["uId"], w["uEstado"])
        if wk != self.wPrev:
            self.wU = None if w["uEstado"] < 0 else Ev(w["uId"], w["uRango"], w["uDir"], 0, 0, w["uObj"], w["uBarr"], "otro", None, w["uEstado"])
            self.wPrev = wk
        mk = (m["uId"], m["uEstado"])
        if mk != self.mPrev:
            self.mU = None if m["uEstado"] < 0 else Ev(m["uId"], m["uRango"], m["uDir"], 0, 0, m["uObj"], m["uBarr"], "otro", None, m["uEstado"])
            self.mPrev = mk
        if self.kWPrev != 0 and kW != self.kWPrev and self.op is not None:
            self.salir(self.cierrePrev if self.op["dir"] > 0 else self.cierrePrev + self.dif, "Cierre semanal", self.diaPrev, b.t)
        for mm, k in ((self.h1, k1), (self.h3, k3), (self.h4, k4), (self.d1, dia)):
            if mm.parcial is not None and k != mm.clave: self.cerrar(mm)
        for u in (self.h1.ultimo, self.h3.ultimo, self.h4.ultimo, self.d1.ultimo, self.wU, self.mU): self.completar(u, b)
        for mm, k in ((self.h1, k1), (self.h3, k3), (self.h4, k4), (self.d1, dia)): self.sumar(mm, b, k)
        tc = b.t + timedelta(minutes=15)
        if self.op is not None:
            o = self.op; dif = self.dif
            ap = b.o if o["dir"] > 0 else b.o + dif; mx = b.h if o["dir"] > 0 else b.h + dif; mn = b.l if o["dir"] > 0 else b.l + dif
            if (o["dir"] > 0 and mn <= o["stop"]) or (o["dir"] < 0 and mx >= o["stop"]):
                self.salir(min(o["stop"], ap) if o["dir"] > 0 else max(o["stop"], ap), "SL", dia, tc)
            elif (o["dir"] > 0 and mx >= o["tp"]) or (o["dir"] < 0 and mn <= o["tp"]):
                self.salir(o["tp"], "TP", dia, tc)
        diaS, wdS, k1S, k3S, k4S, kWS = self.claves(tc)
        finSemana = kWS != kW or wdS >= 5
        for mm, k in ((self.h1, k1S), (self.h3, k3S), (self.h4, k4S), (self.d1, diaS)):
            if k != mm.clave: self.cerrar(mm)
        if finSemana and self.op is not None:
            self.salir(b.c if self.op["dir"] > 0 else b.c + self.dif, "Cierre semanal", dia, tc)
        mc = tc.hour * 60 + tc.minute
        if self.anterior is not None and not finSemana:
            self.mirar(b, self.anterior, 1, dia, mc, tc)
            self.mirar(b, self.anterior, -1, dia, mc, tc)
        self.anterior = b; self.kWPrev = kW; self.diaPrev = dia; self.cierrePrev = b.c
