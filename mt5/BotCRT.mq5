//+------------------------------------------------------------------+
//|                                                     BotCRT.mq5   |
//+------------------------------------------------------------------+
// Bot de la estrategia CRT para MetaTrader 5.
//
// Hace lo mismo que el Python de la carpeta crt/ (la prueba con datos del pasado), paso a paso:
//   - monta sus propias velas de 1H, 4H, diario, semanal y mensual en hora de Nueva York a partir de
//     las barras de 15 minutos del bróker (el día de trading va de 17:00 a 17:00);
//   - busca rangos y rupturas, mira el semáforo del diario y del 4H y el sesgo de fondo;
//   - cuando sale el primer order block de M15 de una idea a favor, avisa al móvil y, si se le
//     pide, opera en una cuenta demo.
//
// Apunta cada situación en la memoria (MQL5/Files/BotCRT/memoria_<mercado>.csv), con las mismas
// columnas y los mismos motivos que la memoria del Python (crt/memoria.py): las señales que toma y
// las que descarta, con sus banderas rojas y su nota (A, B o C). Las descartadas las sigue como
// operaciones «fantasma» hasta su stop o su TP, para saber qué habría pasado. Esa memoria es la que
// revisa Claude para aprender.
//
// Disciplina (vídeo de psicología): tope de pérdida del día entre todos los mercados en los que esté
// puesto el bot (se cuentan con las variables globales de MT5), racha de stops en el panel y, como
// regla candidata, un día de pausa tras una racha.
//
// Las reglas candidatas (las de los vídeos que aún no están aprobadas) están apagadas: no perseguir el
// precio, el lado de la apertura del día, las noticias, el cierre del día, las salidas por tiempo…
//
// Por defecto SOLO AVISA. Nunca opera en una cuenta real salvo que se active a propósito.
//
// Si cambias una regla aquí, cámbiala también en crt/ (y al revés): los dos tienen que decidir igual.
#property copyright   "Damji Systems"
#property version     "1.14"
#property description "Bot CRT: avisa de las entradas de la estrategia CRT y apunta la memoria."
#property description "Por defecto solo avisa. No opera en cuentas reales."

#include <Trade\Trade.mqh>

// ───────────────────────── Parámetros ─────────────────────────

enum ModoBot
  {
   SOLO_AVISOS    = 0,  // Solo avisos
   OPERAR_EN_DEMO = 1   // Operar en una cuenta demo
  };

enum ModoSalida1H
  {
   SALIDA_NO      = 0,  // No
   SALIDA_SALIR   = 1,  // Salir
   SALIDA_ENTRADA = 2   // Stop a la entrada si va ganando; si no, salir
  };

enum Exigencia
  {
   EXIGIR_NADA    = 0,  // No
   EXIGIR_VERDE   = 1,  // Que esté a favor (verde)
   EXIGIR_NO_ROJO = 2   // Que no vaya en contra (no rojo)
  };

enum SesgoEquipo
  {
   SESGO_DEL_BOT  = 0,  // El que calcula el bot
   SESGO_COMPRAS  = 1,  // Compras
   SESGO_VENTAS   = 2,  // Ventas
   SESGO_NINGUNO  = 3   // Ninguno: esta semana no entra
  };

input group "Qué hace el bot"
input ModoBot  Modo                     = SOLO_AVISOS;  // Modo
input bool     PermitirCuentaReal       = false;        // Permitir operar en cuenta real (¡peligro!)
input double   RiesgoPct                = 1.0;          // Riesgo por operación (% del balance)
input string   NombreMercado            = "";           // Nombre del mercado (vacío = el del símbolo)

input group "Reglas"
input SesgoEquipo SesgoDeLaSemana       = SESGO_DEL_BOT; // Sesgo de la semana (lo confirmáis o lo cambiáis cada lunes)
input double   Ratio                    = 2.0;          // TP: veces lo que se arriesga (1 a 2)
input int      EsperaAperturaMin        = 45;           // Minutos sin entrar tras la apertura de las 9:30 (NY)
input string   HoraDesde                = "01:00";      // Entradas desde (hora de Nueva York)
input string   HoraHasta                = "13:00";      // Entradas hasta (hora de Nueva York)
input bool     SoloTrasApertura         = false;        // Solo entradas después de la apertura
input bool     SoloLondres              = false;        // Solo entradas antes de la apertura (Londres)
input int      MaxOperacionesDia        = 2;            // Máximo de operaciones al día
input int      ColchonStopPuntos        = 30;           // Colchón del stop detrás del barrido (puntos)
input bool     DiarioBastaNoRojo        = false;        // Diario: basta con que no vaya en contra
input bool     ComprobarObjetivoDiario  = true;         // No entrar si el TP queda más allá del objetivo del diario
input double   PerdidaMaxDiaR           = 3;            // Tope de pérdida del día entre todos los mercados, en R (0 = sin tope)
input int      HoraInicio4H             = 17;           // Las velas de 4H empiezan a esta hora de NY (17: las de la 1, las 5 y las 9, lo decidido)

input group "Reglas candidatas (apagadas hasta que el laboratorio las apruebe)"
input double   StopAEntradaEnR          = 0;            // Stop a la entrada al llegar a +X R (0 = no)
input double   Vela1Minima              = 0;            // Vela 1 mínima, en veces el tamaño medio de 4H (0 = no)
input bool     SinNoticias              = false;        // No entrar los días con noticias fuertes
input string   EscenariosPermitidos     = "";           // Escenarios permitidos (vacío = todos; p. ej. 1,2)
input ModoSalida1H Salida1H             = SALIDA_NO;    // Si se forma un rango de 1H en contra
input bool     TpEnObjetivo4H           = false;        // TP en el objetivo del rango de 4H (no a 1 a Ratio)
input Exigencia Exigir1H                = EXIGIR_NADA;  // Exigir el 1H
input Exigencia Exigir3H                = EXIGIR_NADA;  // Exigir el 3H
input bool     SoloSinBanderas          = false;        // Solo situaciones sin banderas rojas (nota A)
input int      PausaTrasStops           = 0;            // Un día de pausa tras tantos stops seguidos (0 = no)
input bool     DiarioValeExpansiva      = false;        // Diario: también vale tras una vela diaria expansiva a favor
input bool     SalidaPeligro            = false;        // Salir en la zona de peligro (máximos nuevos de 4H y 1H y barrido en M15)
input double   ToleranciaDiario         = 0;            // Rango diario aunque cierre hasta esta parte de la vela 1 por fuera (0 = no; p. ej. 0.1)
input bool     NoPerseguir              = false;        // Si la entrada queda lejos del barrido, no entrar y esperar otro order block
input bool     SoloLadoDeLaApertura     = false;        // Comprar solo por debajo de la apertura del día y vender solo por encima
input bool     AntesDeNoticias          = false;        // No entrar antes de la primera noticia fuerte del día
input bool     CierreDiario             = false;        // Cerrar lo abierto al final del día (17:00 de NY), como en futuros
input bool     TpHastaObjetivo4H        = false;        // Si el objetivo del 4H está más lejos que el TP, dejar correr hasta él
input bool     SalidaPorTiempo          = false;        // Ganando, salir si una vela de 4H nueva supera el extremo de la anterior a favor
input bool     BreakEvenAntesDeLas9     = false;        // Ganando, stop a la entrada justo antes de la vela de 4H de las 9:00
input bool     ComprobarObjetivo4H      = false;        // No entrar si el TP queda más allá del objetivo del 4H
input bool     VetarTomando             = false;        // No entrar con el diario o el 4H tomando máximos (compras) o mínimos (ventas)
input bool     IgnorarSesgo             = false;        // Sin sesgo de fondo (con IgnorarDiario: el modelo del backtest del autor)
input bool     IgnorarDiario            = false;        // Sin mirar el diario (solo para pruebas)

input group "Datos y memoria"
input int      DesfaseServidorNY        = 7;            // Horas que el servidor va por delante de Nueva York
input int      DiferencialFijoPuntos    = 0;            // Diferencial fijo en puntos (0 = el del bróker)
input int      MesesHistoria            = 24;           // Meses de historia para arrancar
input bool     EscribirMemoriaHistorica = false;        // Apuntar también la historia en la memoria
input bool     ExportarNoticias         = false;        // Exportar las noticias a noticias.csv al arrancar
input int      AniosNoticias            = 3;            // Años de noticias que exportar
input long     NumeroMagico             = 20261020;     // Número de las órdenes del bot

// ───────────────────────── Constantes ─────────────────────────

#define TIPO_RANGO        0
#define TIPO_RUPTURA      1
#define EST_ACTIVO        0
#define EST_COMPLETADO    1
#define EST_ANULADO       2
#define VIA_NINGUNA      -1
#define VIA_CIERRE        0
#define VIA_ANTICIPO      1
#define MARCO_H1          0
#define MARCO_H4          1
#define MARCO_D1          2
#define MARCO_W1          3
#define MARCO_MN          4
#define MARCO_H3          5
#define SEG_M15           900
#define SEG_HORA          3600
#define SEG_DIA           86400
#define DESFASE_DIA       25200      // 17:00 de Nueva York + 7 h = 00:00 del día de trading
#define MAX_VELAS_EVENTO  60         // un rango que lleva tantas velas sin completarse deja de seguirse
#define VELAS_MEDIA       20         // el tamaño «normal» de una vela es la media de las últimas 20
#define MIN_VELAS_MEDIA   5          // con menos velas cerradas no hay media
#define STOP_MINIMO_EN_DIFERENCIALES 3  // un stop más corto que esto se lo comería el diferencial
#define MINIMO_R_OBJETIVO 1.0        // con el TP en el objetivo del 4H, no se entra si está a menos de esto
#define APERTURA_NY_MIN   570        // 9:30 de Nueva York, en minutos
#define MINUTOS_TARDE     20         // una barra que llega con más retraso no avisa ni opera
#define VELA_DE_LAS_9_MIN 540        // 9:00 de Nueva York, en minutos
#define FIN_DEL_DIA_MIN   1020       // 17:00 de Nueva York, en minutos
#define MINUTOS_ANTES_DEL_PARON 5    // en vivo, la posición de la cuenta se cierra estos minutos antes del cierre
#define MAX_IDEAS         4000       // ideas que se recuerdan (usadas y vistas)
#define VACIO             EMPTY_VALUE

// Decisiones: los mismos textos que en crt/motor.py.
#define DEC_NINGUNA      -1
#define DEC_ENTRADA       0
#define DEC_SIN_SESGO     1
#define DEC_DIARIO        2
#define DEC_ABIERTA       3
#define DEC_ESCENARIO     4
#define DEC_VELA1         5
#define DEC_NOTICIAS      6
#define DEC_TOPE          7
#define DEC_BARRIDO       8
#define DEC_STOP_CORTO    9
#define DEC_NO_CABE      10
#define DEC_H3           11
#define DEC_H1           12
#define DEC_BANDERAS     13
#define DEC_OBJETIVO     14
#define DEC_PAUSA        15
#define DEC_PERDIDA      16
#define DEC_LEJOS        17
#define DEC_APERTURA     18
#define DEC_ANTES_NOTICIAS 19
#define DEC_NO_CABE_4H   20

#define RES_NINGUNO       0
#define RES_TP            1
#define RES_SL            2
#define RES_BE            3
#define RES_SEMANAL       4
#define RES_1H            5
#define RES_PELIGRO       6
#define RES_DIA           7
#define RES_TIEMPO        8

// Banderas rojas (crt/motor.py: BANDERAS), en el mismo orden. Se guardan como bits.
#define BAN_DIARIO_EN_CONTRA   1
#define BAN_DIARIO_MAXIMOS     2
#define BAN_DIARIO_MINIMOS     4
#define BAN_4H_MAXIMOS         8
#define BAN_4H_MINIMOS        16
#define BAN_1H_MAXIMOS        32
#define BAN_1H_MINIMOS        64
#define BAN_3H_EN_CONTRA     128
#define BAN_1H_EN_CONTRA     256
#define BAN_APERTURA_COMPRA  512
#define BAN_APERTURA_VENTA  1024
#define BAN_ANTES_APERTURA  2048
#define BAN_LEJOS           4096
#define NUM_BANDERAS          13

#define CABECERA_MEMORIA  "mercado,hora_ny,direccion,decision,sesion,dia_semana,sesgo_semanal,sesgo_mensual,diario,via_diario,via_4h,h3,h1,escenario,vela1_rel,stop_rel,objetivo_r,noticias,banderas,nota,entrada,stop,tp,resultado,r,mfe_r,mae_r,tomada"
#define CABECERA_NOTICIAS "fecha,hora,moneda,evento,importancia"

string DIAS[7] = {"domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"};

// ───────────────────────── Estructuras ─────────────────────────

struct Vela
  {
   datetime          inicio;      // hora de Nueva York, de reloj
   double            apertura;
   double            maximo;
   double            minimo;
   double            cierre;
   int               i_inicio;    // primera barra de M15 de la vela
   int               i_fin;       // última barra de M15 de la vela
   double            dif;         // diferencial de la barra (solo en las barras de M15)
  };

struct Evento
  {
   int               tipo;        // TIPO_RANGO o TIPO_RUPTURA
   int               direccion;   // +1 alcista, -1 bajista
   int               i_formado;   // barra de M15 con la que cerró la vela 2
   int               i_vela_inicio;  // primera barra de M15 de la vela 2
   double            objetivo;
   double            barrido;
   int               escenario;   // 1, 2, 3 o 0 (otro)
   double            vela1_rel;   // tamaño de la vela 1 comparado con la media; VACIO si no hay
   int               estado;
   int               velas_desde;
   int               velas_hasta_completar;  // -1 = sin completar
   long              id;
  };

struct Setup
  {
   long              idea1;       // identifican la idea: la misma idea no da dos entradas
   long              idea2;       // 0 = no hay
   int               direccion;
   double            barrido;     // el stop va detrás
   double            objetivo;
   int               i_inicio;    // la entrada tiene que llegar después de esta barra de M15
   int               via;         // VIA_CIERRE o VIA_ANTICIPO
   int               escenario;
   double            vela1_rel;
  };

// Una situación vista (una fila de la memoria) y, si se pudieron poner niveles, su operación: la
// real (tomada) o una fantasma.
struct Senal
  {
   datetime          hora_ny;
   int               direccion;
   int               decision;
   int               sesgo_sem;   // +1 a favor, 0 neutral, -1 en contra (respecto a la dirección)
   int               sesgo_men;
   int               diario;      // 1 verde, 0 ámbar, -1 rojo (para esta dirección)
   int               via_diario;
   int               via_4h;
   int               h3;          // color del 3H para esta dirección
   int               h1;          // color del 1H para esta dirección
   int               escenario;
   double            vela1_rel;
   double            stop_rel;
   double            objetivo_r;
   int               banderas;    // banderas rojas (bits BAN_*)
   bool              apuntar;     // escribirla en la memoria
   bool              hay_op;
   bool              tomada;
   bool              avisada;
   double            entrada;
   double            stop;        // el de ahora: pasa a la entrada con la regla candidata
   double            stop_inicial;
   double            tp;
   double            riesgo;      // 1 R
   double            dif;
   bool              en_entrada;  // el stop ya está en la entrada
   int               resultado;
   datetime          hora_salida; // hora de Nueva York a la que se cerró
   double            salida;
   double            r;
   double            mfe;         // lo más que llegó a ir a favor, en R
   double            mae;         // lo más que llegó a ir en contra, en R
   ulong             ticket;      // la posición en la cuenta, si se opera
  };

// ───────────────────────── Estado ─────────────────────────

long      g_siguiente_id = 0;

long ClaveAnticipo(const int marco, const int i_inicio, const int dir)
  {
   return ((long)i_inicio * 8 + marco) * 2 + (dir > 0 ? 1 : 0) + 1;
  }

// ───────────────────────── Rangos ─────────────────────────

// El evento que forma la vela 2 respecto a la vela 1 (crt/rangos.py: evaluar). Con «tolerancia», una
// vela 2 que barre un extremo y cierra muy poco por fuera de ese lado sigue contando como rango.
bool Evaluar(const Vela &v1, const Vela &v2, Evento &e, const double tolerancia)
  {
   ZeroMemory(e);
   e.i_formado = v2.i_fin;
   e.i_vela_inicio = v2.i_inicio;
   e.estado = EST_ACTIVO;
   e.velas_hasta_completar = -1;
   e.vela1_rel = VACIO;
   double margen = tolerancia * (v1.maximo - v1.minimo);
   bool toma_minimo = v2.minimo < v1.minimo;
   bool toma_maximo = v2.maximo > v1.maximo;
   if(v2.cierre > v1.maximo && (v2.cierre > v1.maximo + margen || toma_minimo))
     {
      e.tipo = TIPO_RUPTURA;
      e.direccion = 1;
      return true;
     }
   if(v2.cierre < v1.minimo && (v2.cierre < v1.minimo - margen || toma_maximo))
     {
      e.tipo = TIPO_RUPTURA;
      e.direccion = -1;
      return true;
     }
   if(toma_minimo && !toma_maximo)
     {
      e.tipo = TIPO_RANGO;
      e.direccion = 1;
      e.objetivo = v1.maximo;
      e.barrido = v2.minimo;
      return true;
     }
   if(toma_maximo && !toma_minimo)
     {
      e.tipo = TIPO_RANGO;
      e.direccion = -1;
      e.objetivo = v1.minimo;
      e.barrido = v2.maximo;
      return true;
     }
   return false;
  }

// Escenario del primer vídeo según el evento que había antes (crt/rangos.py: escenario).
int EscenarioDe(const Evento &previo, const int dir)
  {
   if(previo.tipo != TIPO_RANGO || previo.direccion == dir)
      return 0;
   if(previo.estado == EST_ACTIVO)
      return 3;
   if(previo.estado == EST_COMPLETADO)
      return previo.velas_hasta_completar == 1 ? 2 : 1;
   return 0;
  }

// Color del semáforo solo con velas cerradas (crt/rangos.py: semaforo): 1 verde, 0 ámbar, -1 rojo.
int SemaforoDe(const Evento &e, const int dir)
  {
   if(e.tipo == TIPO_RUPTURA)
      return e.direccion != dir ? -1 : 0;
   if(e.estado != EST_ACTIVO)
      return 0;
   return e.direccion == dir ? 1 : -1;
  }

// ───────────────────────── Marco de tiempo ─────────────────────────

// Un marco (1H, 4H, diario…) con sus velas, sus rangos y su semáforo (crt/marcos.py: Marco).
class CMarco
  {
public:
   string            nombre;
   int               tipo;
   CMarco           *menor;
   Vela              cerradas[];  // solo las últimas (VELAS_MEDIA + 1)
   Vela              parcial;     // la vela en curso
   bool              hay_parcial;
   datetime          clave;
   datetime          fin_ny;
   Evento            ev[];        // los rangos activos y el último evento
   int               ultimo;      // índice del último evento en ev[], -1 si no hay
   int               i_barrido_alc;  // barra en la que la vela en curso barrió el mínimo de la anterior
   int               i_barrido_baj;  // ... y el máximo
   int               inicio_4h;      // hora de Nueva York a la que empiezan las velas de 4H
   double            tolerancia;     // cierre un poco por fuera que aún cuenta como rango (ver Evaluar)

   void              Iniciar(const string n, const int t, CMarco *m, const int h4 = 17, const double tol = 0);
   void              ClaveYFin(const datetime inicio_ny, datetime &k, datetime &fin);
   bool              TocaCerrarAntes(const Vela &b);
   bool              TocaCerrarDespues(const Vela &b);
   void              ActualizarConBarra(const Vela &b);
   void              Sumar(const Vela &b);
   bool              Cerrar(void);
   bool              DameSetup(const int dir, const double precio, Setup &s);
   bool              DameAnticipo(const int dir, const double precio, Setup &s);
   bool              Tomando(const int dir);
   void              UltimoEvento(Evento &e) { e = ev[ultimo]; }
   bool              UltimaEsRuptura(const int dir) { return ultimo >= 0 && ev[ultimo].tipo == TIPO_RUPTURA && ev[ultimo].direccion == dir; }
   int               ColorSemaforo(const int dir, const double precio);
   int               SemaforoCerrado(const int dir);
   int               DireccionUltimo(void);
   double            RangoMedio(void);
   double            Relativo(const Vela &v);
   int               NCerradas(void) { return ArraySize(cerradas); }
   void              UltimaCerrada(Vela &v) { v = cerradas[ArraySize(cerradas) - 1]; }

private:
   void              Compactar(void);
   void              AgregarCerrada(const Vela &v);
   int               EscenarioDesdeUltimo(const int dir);
  };

void CMarco::Iniciar(const string n, const int t, CMarco *m, const int h4, const double tol)
  {
   nombre = n;
   tipo = t;
   menor = m;
   inicio_4h = h4;
   tolerancia = tol;
   ArrayResize(cerradas, 0);
   ArrayResize(ev, 0);
   ZeroMemory(parcial);
   hay_parcial = false;
   clave = 0;
   fin_ny = 0;
   ultimo = -1;
   i_barrido_alc = -1;
   i_barrido_baj = -1;
  }

// A qué vela pertenece una barra que empieza a esta hora y a qué hora de Nueva York cierra esa vela.
void CMarco::ClaveYFin(const datetime inicio_ny, datetime &k, datetime &fin)
  {
   long t = (long)inicio_ny + DESFASE_DIA;
   long kl = 0;
   long fl = 0;
   if(tipo == MARCO_H4)
     {
      long desfase = (long)(24 - inicio_4h) * SEG_HORA;
      long t4 = (long)inicio_ny + desfase;
      kl = t4 - t4 % (4 * SEG_HORA);
      k = (datetime)kl;
      fin = (datetime)(kl + 4 * SEG_HORA - desfase);
      return;
     }
   if(tipo == MARCO_H1)
     {
      kl = t - t % SEG_HORA;
      fl = kl + SEG_HORA;
     }
   else
      if(tipo == MARCO_H3)
        {
         kl = t - t % (3 * SEG_HORA);
         fl = kl + 3 * SEG_HORA;
        }
      else
         if(tipo == MARCO_D1)
           {
            kl = t - t % SEG_DIA;
            fl = kl + SEG_DIA;
           }
         else
            if(tipo == MARCO_W1)
              {
               long dia = t / SEG_DIA;
               long lunes = dia - (dia + 3) % 7;   // el 1-1-1970 fue jueves
               kl = lunes * SEG_DIA;
               fl = kl + 5 * SEG_DIA;              // sábado 00:00 de trading = viernes 17:00 de Nueva York
              }
            else
              {
               MqlDateTime st;
               TimeToStruct((datetime)t, st);
               st.day = 1;
               st.hour = 0;
               st.min = 0;
               st.sec = 0;
               kl = (long)StructToTime(st);
               st.mon++;
               if(st.mon > 12)
                 {
                  st.mon = 1;
                  st.year++;
                 }
               fl = (long)StructToTime(st);
              }
   k = (datetime)kl;
   fin = (datetime)(fl - DESFASE_DIA);
  }

// La barra pertenece a otra vela: hay que cerrar la que está en curso antes de sumarla.
bool CMarco::TocaCerrarAntes(const Vela &b)
  {
   if(!hay_parcial)
      return false;
   datetime k, f;
   ClaveYFin(b.inicio, k, f);
   return k != clave;
  }

// Con esta barra termina la vela en curso.
bool CMarco::TocaCerrarDespues(const Vela &b)
  {
   return hay_parcial && b.inicio + SEG_M15 >= fin_ny;
  }

// ¿Algún rango ha tocado su objetivo en esta barra?
void CMarco::ActualizarConBarra(const Vela &b)
  {
   int n = ArraySize(ev);
   for(int k = 0; k < n; k++)
     {
      if(ev[k].tipo != TIPO_RANGO || ev[k].estado != EST_ACTIVO || ev[k].i_formado >= b.i_fin)
         continue;
      if((ev[k].direccion > 0 && b.maximo >= ev[k].objetivo) || (ev[k].direccion < 0 && b.minimo <= ev[k].objetivo))
        {
         ev[k].estado = EST_COMPLETADO;
         ev[k].velas_hasta_completar = ev[k].velas_desde + 1;
        }
     }
   Compactar();
  }

void CMarco::Sumar(const Vela &b)
  {
   if(!hay_parcial)
     {
      ClaveYFin(b.inicio, clave, fin_ny);
      parcial = b;
      parcial.dif = 0;
      hay_parcial = true;
      i_barrido_alc = -1;
      i_barrido_baj = -1;
     }
   else
     {
      if(b.maximo > parcial.maximo)
         parcial.maximo = b.maximo;
      if(b.minimo < parcial.minimo)
         parcial.minimo = b.minimo;
      parcial.cierre = b.cierre;
      parcial.i_fin = b.i_fin;
     }
   int n = ArraySize(cerradas);
   if(n > 0)
     {
      if(i_barrido_alc < 0 && parcial.minimo < cerradas[n - 1].minimo)
         i_barrido_alc = b.i_fin;
      if(i_barrido_baj < 0 && parcial.maximo > cerradas[n - 1].maximo)
         i_barrido_baj = b.i_fin;
     }
  }

// Cierra la vela en curso. Devuelve true si forma un evento nuevo (que queda como el último).
bool CMarco::Cerrar(void)
  {
   Vela vela = parcial;
   hay_parcial = false;
   int n = ArraySize(ev);
   for(int k = 0; k < n; k++)
     {
      if(ev[k].tipo != TIPO_RANGO || ev[k].estado != EST_ACTIVO)
         continue;
      ev[k].velas_desde++;
      if((ev[k].direccion > 0 && vela.cierre < ev[k].barrido) || (ev[k].direccion < 0 && vela.cierre > ev[k].barrido))
         ev[k].estado = EST_ANULADO;   // cerró con el cuerpo más allá del barrido
     }
   Compactar();
   Evento nuevo;
   bool hay_nuevo = false;
   int nc = ArraySize(cerradas);
   if(nc > 0)
     {
      hay_nuevo = Evaluar(cerradas[nc - 1], vela, nuevo, tolerancia);
      if(hay_nuevo)
         nuevo.vela1_rel = Relativo(cerradas[nc - 1]);
     }
   AgregarCerrada(vela);
   if(hay_nuevo)
     {
      nuevo.escenario = EscenarioDesdeUltimo(nuevo.direccion);
      g_siguiente_id++;
      nuevo.id = g_siguiente_id;
      int m = ArraySize(ev);
      ArrayResize(ev, m + 1);
      ev[m] = nuevo;
      ultimo = m;
     }
   return hay_nuevo;
  }

// Quita los rangos que ya no hay que seguir. El último evento se queda siempre.
void CMarco::Compactar(void)
  {
   int n = ArraySize(ev);
   int j = 0;
   int nuevo_ultimo = -1;
   for(int k = 0; k < n; k++)
     {
      bool es_ultimo = (k == ultimo);
      bool sigue = ev[k].tipo == TIPO_RANGO && ev[k].estado == EST_ACTIVO && ev[k].velas_desde < MAX_VELAS_EVENTO;
      if(!es_ultimo && !sigue)
         continue;
      if(j != k)
         ev[j] = ev[k];
      if(es_ultimo)
         nuevo_ultimo = j;
      j++;
     }
   ArrayResize(ev, j);
   ultimo = nuevo_ultimo;
  }

void CMarco::AgregarCerrada(const Vela &v)
  {
   int n = ArraySize(cerradas);
   if(n >= VELAS_MEDIA + 1)
     {
      for(int k = 1; k < n; k++)
         cerradas[k - 1] = cerradas[k];
      cerradas[n - 1] = v;
     }
   else
     {
      ArrayResize(cerradas, n + 1);
      cerradas[n] = v;
     }
  }

// Tamaño medio (máximo − mínimo) de las últimas velas cerradas, o VACIO si aún hay pocas.
double CMarco::RangoMedio(void)
  {
   int n = ArraySize(cerradas);
   int desde = n - VELAS_MEDIA;
   if(desde < 0)
      desde = 0;
   int cuantas = n - desde;
   if(cuantas < MIN_VELAS_MEDIA)
      return VACIO;
   double suma = 0;
   for(int k = desde; k < n; k++)
      suma += cerradas[k].maximo - cerradas[k].minimo;
   return suma / cuantas;
  }

double CMarco::Relativo(const Vela &v)
  {
   double medio = RangoMedio();
   if(medio == VACIO || medio == 0)
      return VACIO;
   return (v.maximo - v.minimo) / medio;
  }

int CMarco::EscenarioDesdeUltimo(const int dir)
  {
   if(ultimo < 0)
      return 0;
   return EscenarioDe(ev[ultimo], dir);
  }

// El rango a favor desde el que buscar la entrada ahora mismo: cerrado, o anticipado con el marco
// menor (crt/marcos.py: setup).
bool CMarco::DameSetup(const int dir, const double precio, Setup &s)
  {
   ZeroMemory(s);
   if(ultimo >= 0 && ev[ultimo].tipo == TIPO_RANGO && ev[ultimo].estado == EST_ACTIVO && ev[ultimo].direccion == dir)
     {
      s.idea1 = -ev[ultimo].id;
      s.idea2 = ClaveAnticipo(tipo, ev[ultimo].i_vela_inicio, dir);
      s.direccion = dir;
      s.barrido = ev[ultimo].barrido;
      s.objetivo = ev[ultimo].objetivo;
      s.i_inicio = ev[ultimo].i_formado;
      s.via = VIA_CIERRE;
      s.escenario = ev[ultimo].escenario;
      s.vela1_rel = ev[ultimo].vela1_rel;
      return true;
     }
   return DameAnticipo(dir, precio, s);
  }

// El rango a favor que está formando la vela en curso, visto con el marco menor: ya barrió el extremo
// de la anterior (sin tomar también el otro, porque entonces no puede ser rango), el precio volvió
// dentro y el marco menor formó un rango a favor después del barrido (crt/marcos.py: anticipo).
bool CMarco::DameAnticipo(const int dir, const double precio, Setup &s)
  {
   ZeroMemory(s);
   int nc = ArraySize(cerradas);
   if(menor == NULL || !hay_parcial || nc == 0)
      return false;
   int ib = (dir > 0) ? i_barrido_alc : i_barrido_baj;
   Vela previa = cerradas[nc - 1];
   if(ib < 0 || !(previa.minimo < precio && precio < previa.maximo) || Tomando(dir))
      return false;
   Setup sm;
   if(!menor.DameSetup(dir, precio, sm))
      return false;
   if(sm.i_inicio < ib)
      return false;
   s.idea1 = ClaveAnticipo(tipo, parcial.i_inicio, dir);
   s.idea2 = 0;
   s.direccion = dir;
   s.barrido = (dir > 0) ? parcial.minimo : parcial.maximo;
   s.objetivo = (dir > 0) ? previa.maximo : previa.minimo;
   s.i_inicio = sm.i_inicio;
   s.via = VIA_ANTICIPO;
   s.escenario = EscenarioDesdeUltimo(dir);
   s.vela1_rel = Relativo(previa);
   return true;
  }

// ¿La vela en curso ya ha pasado el extremo de la anterior hacia ese lado? En compras, que está
// «tomando máximos»: si vuelve a cerrar dentro, forma un rango en contra.
bool CMarco::Tomando(const int dir)
  {
   int nc = ArraySize(cerradas);
   if(!hay_parcial || nc == 0)
      return false;
   if(dir > 0)
      return parcial.maximo > cerradas[nc - 1].maximo;
   return parcial.minimo < cerradas[nc - 1].minimo;
  }

int CMarco::SemaforoCerrado(const int dir)
  {
   if(ultimo < 0)
      return 0;
   return SemaforoDe(ev[ultimo], dir);
  }

int CMarco::ColorSemaforo(const int dir, const double precio)
  {
   Setup s;
   if(DameSetup(dir, precio, s))
      return 1;
   return SemaforoCerrado(dir);
  }

// Hacia dónde empuja el último evento: un rango activo, hacia su objetivo; una ruptura, en su
// dirección (crt/motor.py: direccion_de).
int CMarco::DireccionUltimo(void)
  {
   if(ultimo < 0)
      return 0;
   if(ev[ultimo].tipo == TIPO_RUPTURA)
      return ev[ultimo].direccion;
   return ev[ultimo].estado == EST_ACTIVO ? ev[ultimo].direccion : 0;
  }

// ───────────────────────── Estado del bot ─────────────────────────

CMarco    g_h1;
CMarco    g_h3;
CMarco    g_h4;
CMarco    g_d1;
CMarco    g_w1;
CMarco    g_mn;
CTrade    g_trade;

Vela      g_anterior;
bool      g_hay_anterior = false;
int       g_i = 0;                   // número de la próxima barra de M15
bool      g_hay_real = false;
Senal     g_real;                    // la operación del bot
Senal     g_fantasmas[];             // las señales descartadas que se siguen para aprender
long      g_usadas[];                // ideas que ya dieron su entrada (o se descartaron al intentarla)
long      g_vistas[];                // ideas que ya están en la memoria
long      g_dia_ops = -1;
int       g_ops_dia = 0;
long      g_dia_r = -1;              // día de trading de g_r_dia
double    g_r_dia = 0;               // resultado en R de las operaciones de este mercado cerradas ese día
int       g_racha = 0;               // stops seguidos de las operaciones tomadas
long      g_pausa_hasta = -1;        // con la regla de la pausa: último día de trading sin operar
long      g_dia_aviso_tope = -1;     // día en el que ya se avisó del tope de pérdida
bool      g_listo = false;
datetime  g_ultima_barra = 0;        // hora del servidor de la última barra procesada
bool      g_en_vivo = false;
bool      g_tardia = false;
string    g_mercado = "";
string    g_ruta_memoria = "";
string    g_ultima_senal = "";
int       g_desde_min = 60;
int       g_hasta_min = 780;
bool      g_esc_ok[4];               // escenarios permitidos: 0 = otro, 1, 2 y 3

long      g_not_dia[];               // noticias ya leídas, por día de Nueva York
string    g_not_texto[];
ulong     g_cal_id[];                // eventos del calendario ya consultados
bool      g_cal_alta[];
int       g_cal_modo[];
string    g_cal_nombre[];

// ───────────────────────── Ayudas ─────────────────────────

string FechaHora(const datetime t)
  {
   MqlDateTime st;
   TimeToStruct(t, st);
   return StringFormat("%04d-%02d-%02d %02d:%02d", st.year, st.mon, st.day, st.hour, st.min);
  }

string Fecha(const datetime t)
  {
   MqlDateTime st;
   TimeToStruct(t, st);
   return StringFormat("%04d-%02d-%02d", st.year, st.mon, st.day);
  }

string HoraMin(const datetime t)
  {
   MqlDateTime st;
   TimeToStruct(t, st);
   return StringFormat("%02d:%02d", st.hour, st.min);
  }

int MinutosDelDia(const datetime t)
  {
   MqlDateTime st;
   TimeToStruct(t, st);
   return st.hour * 60 + st.min;
  }

long DiaNY(const datetime t) { return (long)t / SEG_DIA; }

// Día al que pertenece una barra: va de las 17:00 a las 17:00 de Nueva York.
long DiaDeTrading(const datetime inicio_ny) { return ((long)inicio_ny + DESFASE_DIA) / SEG_DIA; }

string DiaSemana(const datetime t)
  {
   MqlDateTime st;
   TimeToStruct(t, st);
   return DIAS[st.day_of_week];
  }

string Sesion(const datetime hora_ny)
  {
   return MinutosDelDia(hora_ny) <= APERTURA_NY_MIN ? "Londres" : "Tras la apertura";
  }

string TextoDecision(const int d)
  {
   switch(d)
     {
      case DEC_ENTRADA:
         return "entrada";
      case DEC_SIN_SESGO:
         return "sin sesgo a favor";
      case DEC_DIARIO:
         return "el diario no está a favor";
      case DEC_ABIERTA:
         return "ya había una operación abierta";
      case DEC_ESCENARIO:
         return "escenario no permitido";
      case DEC_VELA1:
         return "vela 1 pequeña";
      case DEC_NOTICIAS:
         return "día de noticias fuertes";
      case DEC_TOPE:
         return "tope de operaciones del día";
      case DEC_BARRIDO:
         return "el precio ya pasó el barrido";
      case DEC_STOP_CORTO:
         return "stop demasiado corto";
      case DEC_NO_CABE:
         return "el TP no cabe antes del objetivo del diario";
      case DEC_H3:
         return "el 3H no acompaña";
      case DEC_H1:
         return "el 1H no acompaña";
      case DEC_BANDERAS:
         return "situación con banderas rojas";
      case DEC_OBJETIVO:
         return "el objetivo del 4H está a menos de 1 R";
      case DEC_PAUSA:
         return "pausa tras una racha de stops";
      case DEC_PERDIDA:
         return "tope de pérdida del día";
      case DEC_LEJOS:
         return "la entrada queda lejos del barrido";
      case DEC_APERTURA:
         return "al otro lado de la apertura del día";
      case DEC_ANTES_NOTICIAS:
         return "antes de una noticia fuerte";
      case DEC_NO_CABE_4H:
         return "el TP no cabe antes del objetivo del 4H";
     }
   return "";
  }

string TextoResultado(const int r)
  {
   switch(r)
     {
      case RES_TP:
         return "TP";
      case RES_SL:
         return "SL";
      case RES_BE:
         return "BE";
      case RES_SEMANAL:
         return "Cierre semanal";
      case RES_1H:
         return "Salida por 1H";
      case RES_PELIGRO:
         return "Zona de peligro";
      case RES_DIA:
         return "Cierre del día";
      case RES_TIEMPO:
         return "Salida por tiempo";
     }
   return "";
  }

string TextoBandera(const int b)
  {
   switch(b)
     {
      case BAN_DIARIO_EN_CONTRA:
         return "el diario va en contra";
      case BAN_DIARIO_MAXIMOS:
         return "el diario está tomando máximos";
      case BAN_DIARIO_MINIMOS:
         return "el diario está tomando mínimos";
      case BAN_4H_MAXIMOS:
         return "el 4H está tomando máximos";
      case BAN_4H_MINIMOS:
         return "el 4H está tomando mínimos";
      case BAN_1H_MAXIMOS:
         return "el 1H está tomando máximos";
      case BAN_1H_MINIMOS:
         return "el 1H está tomando mínimos";
      case BAN_3H_EN_CONTRA:
         return "el 3H va en contra";
      case BAN_1H_EN_CONTRA:
         return "el 1H va en contra";
      case BAN_APERTURA_COMPRA:
         return "compra por encima de la apertura del día";
      case BAN_APERTURA_VENTA:
         return "venta por debajo de la apertura del día";
      case BAN_ANTES_APERTURA:
         return "justo antes de la apertura";
      case BAN_LEJOS:
         return "entrada lejos del barrido";
     }
   return "";
  }

// «el 3H va en contra | justo antes de la apertura», en el mismo orden que el Python.
string TextoBanderas(const int banderas)
  {
   string t = "";
   for(int k = 0; k < NUM_BANDERAS; k++)
     {
      int bit = 1 << k;
      if((banderas & bit) == 0)
         continue;
      t += (t == "") ? TextoBandera(bit) : " | " + TextoBandera(bit);
     }
   return t;
  }

// A: sin banderas rojas; B: con una; C: con dos o más.
string Nota(const int banderas)
  {
   int n = 0;
   for(int k = 0; k < NUM_BANDERAS; k++)
      if((banderas & (1 << k)) != 0)
         n++;
   if(n == 0)
      return "A";
   return (n == 1) ? "B" : "C";
  }

string TextoVia(const int via)
  {
   if(via == VIA_CIERRE)
      return "cierre";
   if(via == VIA_ANTICIPO)
      return "anticipo";
   return "";
  }

string TextoEscenario(const int e) { return e == 0 ? "otro" : IntegerToString(e); }

string TextoColor(const int c)
  {
   if(c > 0)
      return "verde";
   if(c < 0)
      return "rojo";
   return "ambar";
  }

string TextoSesgo(const int s)
  {
   if(s > 0)
      return "a favor";
   if(s < 0)
      return "en contra";
   return "neutral";
  }

string TextoDireccion(const int d)
  {
   if(d > 0)
      return "compras";
   if(d < 0)
      return "ventas";
   return "nada";
  }

string Numero(const double x) { return x == VACIO ? "" : DoubleToString(x, 2); }

// -1.5 → «-1,5 R»; 2 → «+2,0 R»
string NumeroR(const double x)
  {
   string t = (x >= 0 ? "+" : "") + DoubleToString(x, 1);
   StringReplace(t, ".", ",");
   return t + " R";
  }

string Precio(const double x) { return DoubleToString(x, _Digits); }

// 2 → «2»; 1.5 → «1,5»
string NumeroCorto(const double x)
  {
   if(MathAbs(x - MathRound(x)) < 1e-9)
      return IntegerToString((long)MathRound(x));
   string t = DoubleToString(x, 1);
   StringReplace(t, ".", ",");
   return t;
  }

// Un campo de CSV como lo escribe Python: entre comillas solo si lleva comas, comillas o saltos.
string Csv(const string campo)
  {
   if(StringFind(campo, ",") < 0 && StringFind(campo, "\"") < 0 && StringFind(campo, "\n") < 0 && StringFind(campo, "\r") < 0)
      return campo;
   string c = campo;
   StringReplace(c, "\"", "\"\"");
   return "\"" + c + "\"";
  }

string NombreDeArchivo(const string s)
  {
   string r = s;
   string malos = "\\/:*?\"<>| ";
   for(int k = 0; k < StringLen(malos); k++)
      StringReplace(r, StringSubstr(malos, k, 1), "_");
   return r;
  }

// «HH:MM» → minutos desde la medianoche, o -1 si no vale.
int LeerHora(const string texto)
  {
   string partes[];
   if(StringSplit(texto, ':', partes) != 2)
      return -1;
   int h = (int)StringToInteger(partes[0]);
   int m = (int)StringToInteger(partes[1]);
   if(h < 0 || h > 23 || m < 0 || m > 59)
      return -1;
   return h * 60 + m;
  }

void LeerEscenarios(void)
  {
   bool todos = (StringLen(EscenariosPermitidos) == 0);
   for(int k = 0; k < 4; k++)
      g_esc_ok[k] = todos;
   if(todos)
      return;
   string partes[];
   int n = StringSplit(EscenariosPermitidos, ',', partes);
   for(int k = 0; k < n; k++)
     {
      string p = partes[k];
      StringTrimLeft(p);
      StringTrimRight(p);
      StringToLower(p);
      if(p == "otro")
         g_esc_ok[0] = true;
      else
         if(p == "1" || p == "2" || p == "3")
            g_esc_ok[(int)StringToInteger(p)] = true;
     }
  }

bool Contiene(const long &lista[], const long x)
  {
   for(int k = ArraySize(lista) - 1; k >= 0; k--)
      if(lista[k] == x)
         return true;
   return false;
  }

void Anadir(long &lista[], const long x)
  {
   if(x == 0 || Contiene(lista, x))
      return;
   int n = ArraySize(lista);
   if(n >= MAX_IDEAS)   // las ideas muy antiguas ya no pueden volver: se olvidan las primeras
     {
      for(int k = 1; k < n; k++)
         lista[k - 1] = lista[k];
      lista[n - 1] = x;
      return;
     }
   ArrayResize(lista, n + 1);
   lista[n] = x;
  }

bool IdeaEn(const long &lista[], const Setup &s)
  {
   return Contiene(lista, s.idea1) || (s.idea2 != 0 && Contiene(lista, s.idea2));
  }

void MarcarIdea(long &lista[], const Setup &s)
  {
   Anadir(lista, s.idea1);
   if(s.idea2 != 0)
      Anadir(lista, s.idea2);
  }

// ───────────────────────── Archivos (UTF-8, como el Python) ─────────────────────────

void EscribirUtf8(const int h, const string texto)
  {
   uchar bytes[];
   int n = StringToCharArray(texto, bytes, 0, WHOLE_ARRAY, CP_UTF8);
   if(n > 0 && bytes[n - 1] == 0)
      n--;
   if(n > 0)
      FileWriteArray(h, bytes, 0, (uint)n);
  }

// Añade una línea al final del archivo; si el archivo está vacío, pone antes la cabecera.
bool EscribirLinea(const string ruta, const string linea, const string cabecera)
  {
   int h = FileOpen(ruta, FILE_READ | FILE_WRITE | FILE_BIN);
   if(h == INVALID_HANDLE)
     {
      Print("BotCRT: no puedo escribir en ", ruta, " (error ", GetLastError(), ").");
      return false;
     }
   if(FileSize(h) == 0 && cabecera != "")
      EscribirUtf8(h, cabecera + "\r\n");
   FileSeek(h, 0, SEEK_END);
   EscribirUtf8(h, linea + "\r\n");
   FileClose(h);
   return true;
  }

// ───────────────────────── Noticias (calendario económico de MT5) ─────────────────────────

// Índice del evento en la caché, o -1 si no se puede leer.
int EventoCalendario(const ulong id)
  {
   for(int k = ArraySize(g_cal_id) - 1; k >= 0; k--)
      if(g_cal_id[k] == id)
         return k;
   MqlCalendarEvent evento;
   if(!CalendarEventById(id, evento))
      return -1;
   int n = ArraySize(g_cal_id);
   ArrayResize(g_cal_id, n + 1);
   ArrayResize(g_cal_alta, n + 1);
   ArrayResize(g_cal_modo, n + 1);
   ArrayResize(g_cal_nombre, n + 1);
   g_cal_id[n] = id;
   g_cal_alta[n] = (evento.importance == CALENDAR_IMPORTANCE_HIGH);
   g_cal_modo[n] = (int)evento.time_mode;
   g_cal_nombre[n] = evento.name;
   return n;
  }

// Hora de Nueva York de una noticia. Las que no tienen hora exacta se quedan en su día, sin hora.
void HoraDeNoticia(const MqlCalendarValue &v, const int modo, datetime &orden, string &fecha, string &hora)
  {
   if(modo == CALENDAR_TIMEMODE_DATETIME)
     {
      datetime ny = (datetime)((long)v.time - (long)DesfaseServidorNY * SEG_HORA);
      orden = ny;
      fecha = Fecha(ny);
      hora = HoraMin(ny);
     }
   else
     {
      datetime d0 = (datetime)(((long)v.time / SEG_DIA) * SEG_DIA);
      orden = d0;
      fecha = Fecha(d0);
      hora = "";
     }
  }

// Mete una noticia en las listas, ordenada por hora (si coinciden, se queda detrás de las que ya había).
void InsertarNoticia(const datetime o, const string f, const string h, const string mon, const string nom,
                     datetime &orden[], string &fechas[], string &horas[], string &monedas[], string &nombres[])
  {
   int n = ArraySize(orden);
   int p = n;
   while(p > 0 && orden[p - 1] > o)
      p--;
   ArrayResize(orden, n + 1);
   ArrayResize(fechas, n + 1);
   ArrayResize(horas, n + 1);
   ArrayResize(monedas, n + 1);
   ArrayResize(nombres, n + 1);
   for(int k = n; k > p; k--)
     {
      orden[k] = orden[k - 1];
      fechas[k] = fechas[k - 1];
      horas[k] = horas[k - 1];
      monedas[k] = monedas[k - 1];
      nombres[k] = nombres[k - 1];
     }
   orden[p] = o;
   fechas[p] = f;
   horas[p] = h;
   monedas[p] = mon;
   nombres[p] = nom;
  }

// Las noticias de importancia alta de una moneda entre dos horas del servidor.
void RecogerNoticias(const string moneda, const datetime desde, const datetime hasta,
                     datetime &orden[], string &fechas[], string &horas[], string &monedas[], string &nombres[])
  {
   MqlCalendarValue valores[];
   if(!CalendarValueHistory(valores, desde, hasta, NULL, moneda))
      return;
   int n = ArraySize(valores);
   for(int k = 0; k < n; k++)
     {
      int c = EventoCalendario(valores[k].event_id);
      if(c < 0 || !g_cal_alta[c])
         continue;
      datetime o;
      string f, h;
      HoraDeNoticia(valores[k], g_cal_modo[c], o, f, h);
      InsertarNoticia(o, f, h, moneda, g_cal_nombre[c], orden, fechas, horas, monedas, nombres);
     }
  }

// «08:30 Nonfarm Payrolls | 14:00 Fed Interest Rate Decision», como en crt/noticias.py.
string LeerNoticiasDelDia(const long dia)
  {
   if(MQLInfoInteger(MQL_TESTER) != 0)
      return "";   // en el probador de estrategias no hay calendario
   datetime orden[];
   string fechas[];
   string horas[];
   string monedas[];
   string nombres[];
   datetime desde = (datetime)(dia * SEG_DIA);
   datetime hasta = (datetime)(dia * SEG_DIA + SEG_DIA + (long)DesfaseServidorNY * SEG_HORA);
   RecogerNoticias("USD", desde, hasta, orden, fechas, horas, monedas, nombres);
   if(StringFind(_Symbol, "EUR") >= 0)
      RecogerNoticias("EUR", desde, hasta, orden, fechas, horas, monedas, nombres);
   if(StringFind(_Symbol, "GBP") >= 0)
      RecogerNoticias("GBP", desde, hasta, orden, fechas, horas, monedas, nombres);
   string texto = "";
   for(int k = 0; k < ArraySize(orden); k++)
     {
      if(DiaNY(orden[k]) != dia)
         continue;
      string item = (horas[k] == "") ? nombres[k] : horas[k] + " " + nombres[k];
      texto += (texto == "") ? item : " | " + item;
     }
   return texto;
  }

string NoticiasDelDia(const datetime hora_ny)
  {
   long dia = DiaNY(hora_ny);
   for(int k = ArraySize(g_not_dia) - 1; k >= 0; k--)
      if(g_not_dia[k] == dia)
         return g_not_texto[k];
   string texto = LeerNoticiasDelDia(dia);
   int n = ArraySize(g_not_dia);
   if(n >= 500)
     {
      ArrayResize(g_not_dia, 0);
      ArrayResize(g_not_texto, 0);
      n = 0;
     }
   ArrayResize(g_not_dia, n + 1);
   ArrayResize(g_not_texto, n + 1);
   g_not_dia[n] = dia;
   g_not_texto[n] = texto;
   return texto;
  }

// La hora de la primera noticia del día («08:30 Nonfarm Payrolls | …»), en minutos, o -1 si ninguna
// la lleva (crt/motor.py: _primera_hora).
int PrimeraHoraDeNoticias(const string texto)
  {
   string items[];
   int n = StringSplit(texto, '|', items);
   int primera = -1;
   for(int k = 0; k < n; k++)
     {
      string item = items[k];
      StringTrimLeft(item);
      StringTrimRight(item);
      if(StringLen(item) < 5 || StringGetCharacter(item, 2) != ':')
         continue;
      bool cifras = true;
      for(int j = 0; j < 5; j++)
         if(j != 2 && (StringGetCharacter(item, j) < '0' || StringGetCharacter(item, j) > '9'))
            cifras = false;
      int m = cifras ? LeerHora(StringSubstr(item, 0, 5)) : -1;
      if(m >= 0 && (primera < 0 || m < primera))
         primera = m;
     }
   return primera;
  }

// Exporta las noticias fuertes de USD, EUR y GBP a MQL5/Files/BotCRT/noticias.csv para el laboratorio.
void ExportarNoticiasCsv(void)
  {
   if(MQLInfoInteger(MQL_TESTER) != 0)
      return;
   datetime orden[];
   string fechas[];
   string horas[];
   string monedas[];
   string nombres[];
   datetime ahora = TimeTradeServer();
   long trozo = (long)365 * SEG_DIA;
   long inicio = (long)ahora - (long)AniosNoticias * trozo;
   string mons[3] = {"USD", "EUR", "GBP"};
   for(int c = 0; c < 3; c++)
      for(long a = inicio; a < (long)ahora; a += trozo)
        {
         long b = a + trozo - 1;
         if(b > (long)ahora)
            b = (long)ahora;
         RecogerNoticias(mons[c], (datetime)a, (datetime)b, orden, fechas, horas, monedas, nombres);
        }
   string ruta = "BotCRT\\noticias.csv";
   int h = FileOpen(ruta, FILE_WRITE | FILE_BIN);
   if(h == INVALID_HANDLE)
     {
      Print("BotCRT: no puedo escribir ", ruta, " (error ", GetLastError(), ").");
      return;
     }
   EscribirUtf8(h, CABECERA_NOTICIAS + "\r\n");
   for(int k = 0; k < ArraySize(orden); k++)
      EscribirUtf8(h, fechas[k] + "," + horas[k] + "," + monedas[k] + "," + Csv(nombres[k]) + ",alta\r\n");
   FileClose(h);
   Print("BotCRT: ", ArraySize(orden), " noticias fuertes exportadas a MQL5/Files/", ruta);
  }

// ───────────────────────── Horario y gatillo ─────────────────────────

// ¿Puede entrar el bot al cierre de una barra que termina a esta hora? (crt/entrada.py)
bool HoraPermitida(const datetime hora_ny)
  {
   int m = MinutosDelDia(hora_ny);
   if(!(g_desde_min < m && m <= g_hasta_min))
      return false;
   if(EsperaAperturaMin > 0 && APERTURA_NY_MIN < m && m < APERTURA_NY_MIN + EsperaAperturaMin)
      return false;
   if(SoloLondres && m > APERTURA_NY_MIN)
      return false;
   return !(SoloTrasApertura && m <= APERTURA_NY_MIN);
  }

// Order block de M15 a favor: en compras, una vela roja y justo después una verde más fuerte (cuerpo
// más grande) que cierra por encima de donde abrió la roja. En ventas, al revés.
bool EsOrderBlock(const Vela &anterior, const Vela &actual, const int dir)
  {
   double cuerpo_anterior = MathAbs(anterior.cierre - anterior.apertura);
   double cuerpo_actual = MathAbs(actual.cierre - actual.apertura);
   if(cuerpo_actual <= cuerpo_anterior)
      return false;
   bool roja = anterior.cierre < anterior.apertura;
   bool verde = anterior.cierre > anterior.apertura;
   if(dir > 0)
      return roja && actual.cierre > actual.apertura && actual.cierre > anterior.apertura;
   return verde && actual.cierre < actual.apertura && actual.cierre < anterior.apertura;
  }

// Manda el semanal; si no dice nada, el mensual. Si se contradicen, no hay sesgo y no se opera.
int SesgoDelBot(void)
  {
   int s = g_w1.DireccionUltimo();
   int m = g_mn.DireccionUltimo();
   if(s == 0)
      return m;
   return (m == -s) ? 0 : s;
  }

// El sesgo con el que entra: el del bot o, en directo, el que haya puesto el equipo el lunes (decidido el
// 19-10-2026: el bot lo calcula y el equipo lo confirma). La historia se repasa siempre con el del bot.
int SesgoDeFondo(void)
  {
   if(!g_en_vivo || SesgoDeLaSemana == SESGO_DEL_BOT)
      return SesgoDelBot();
   if(SesgoDeLaSemana == SESGO_COMPRAS)
      return 1;
   return (SesgoDeLaSemana == SESGO_VENTAS) ? -1 : 0;
  }

int OperacionesDelDia(const long dia) { return dia == g_dia_ops ? g_ops_dia : 0; }

void SumarOperacionDelDia(const long dia)
  {
   if(dia != g_dia_ops)
     {
      g_dia_ops = dia;
      g_ops_dia = 0;
     }
   g_ops_dia++;
  }

datetime AhoraNY(void) { return (datetime)((long)TimeTradeServer() - (long)DesfaseServidorNY * SEG_HORA); }

// El siguiente día de trading de lunes a viernes (el 1-1-1970 fue jueves).
long SiguienteDiaHabil(const long dia)
  {
   long d = dia + 1;
   while((d + 4) % 7 == 0 || (d + 4) % 7 == 6)
      d++;
   return d;
  }

// ¿El color de un marco (1 verde, 0 ámbar, -1 rojo) cumple lo que se exige?
bool Acompana(const int c, const Exigencia e)
  {
   if(e == EXIGIR_VERDE)
      return c == 1;
   return c != -1;
  }

// Variable global de MT5 con lo que lleva este mercado ese día: así cada bot ve lo de los demás.
string VariableDelDia(const long dia) { return "BotCRT.R." + IntegerToString(dia) + "." + NombreDeArchivo(g_mercado); }

// Resultado en R de las operaciones cerradas ese día. En directo suma todos los mercados en los que
// esté puesto el bot; en la historia, solo este, como la prueba en Python.
double ResultadoDelDia(const long dia)
  {
   double r = (dia == g_dia_r) ? g_r_dia : 0.0;
   if(!g_en_vivo || MQLInfoInteger(MQL_TESTER) != 0)
      return r;
   string prefijo = "BotCRT.R." + IntegerToString(dia) + ".";
   string propia = VariableDelDia(dia);
   for(int k = GlobalVariablesTotal() - 1; k >= 0; k--)
     {
      string nombre = GlobalVariableName(k);
      if(StringFind(nombre, prefijo) == 0 && nombre != propia)
         r += GlobalVariableGet(nombre);
     }
   return r;
  }

// ───────────────────────── Memoria ─────────────────────────

// Escribe una fila de la memoria con las mismas columnas que crt/memoria.py.
void Apuntar(const Senal &s)
  {
   bool cerrada = s.hay_op && s.resultado != RES_NINGUNO;
   string l = Csv(g_mercado);
   l += "," + FechaHora(s.hora_ny);
   l += "," + (s.direccion > 0 ? "compra" : "venta");
   l += "," + Csv(TextoDecision(s.decision));
   l += "," + Sesion(s.hora_ny);
   l += "," + DiaSemana(s.hora_ny);
   l += "," + TextoSesgo(s.sesgo_sem);
   l += "," + TextoSesgo(s.sesgo_men);
   l += "," + TextoColor(s.diario);
   l += "," + TextoVia(s.via_diario);
   l += "," + TextoVia(s.via_4h);
   l += "," + TextoColor(s.h3);
   l += "," + TextoColor(s.h1);
   l += "," + TextoEscenario(s.escenario);
   l += "," + Numero(s.vela1_rel);
   l += "," + Numero(s.stop_rel);
   l += "," + Numero(s.objetivo_r);
   l += "," + Csv(NoticiasDelDia(s.hora_ny));
   l += "," + Csv(TextoBanderas(s.banderas));
   l += "," + Nota(s.banderas);
   l += "," + (s.hay_op ? Precio(s.entrada) : "");
   l += "," + (s.hay_op ? Precio(s.stop_inicial) : "");
   l += "," + (s.hay_op ? Precio(s.tp) : "");
   l += "," + (s.hay_op ? TextoResultado(s.resultado) : "");
   l += "," + (cerrada ? Numero(s.r) : "");
   l += "," + (cerrada ? Numero(s.mfe) : "");
   l += "," + (cerrada ? Numero(s.mae) : "");
   l += "," + ((s.hay_op && s.tomada) ? "si" : "no");
   EscribirLinea(g_ruta_memoria, l, CABECERA_MEMORIA);
  }

// ───────────────────────── Avisos y órdenes ─────────────────────────

bool EsCuentaDemo(void) { return AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_DEMO; }

bool PuedeOperar(void)
  {
   if(Modo != OPERAR_EN_DEMO)
      return false;
   if(EsCuentaDemo())
      return true;
   return PermitirCuentaReal;
  }

int DecimalesVolumen(void)
  {
   double paso = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   int d = 0;
   while(d < 8 && MathAbs(paso - MathRound(paso)) > 1e-8)
     {
      paso *= 10;
      d++;
     }
   return d;
  }

// Lotes para arriesgar RiesgoPct del balance con este stop (0 si no se puede calcular).
double Lotes(const Senal &s)
  {
   double perdida = 0;
   ENUM_ORDER_TYPE tipo = (s.direccion > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(!OrderCalcProfit(tipo, _Symbol, 1.0, s.entrada, s.stop_inicial, perdida) || perdida >= 0)
      return 0;
   double dinero = AccountInfoDouble(ACCOUNT_BALANCE) * RiesgoPct / 100.0;
   double lotes = dinero / MathAbs(perdida);
   double paso = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(paso > 0)
      lotes = MathFloor(lotes / paso + 1e-9) * paso;
   double maximo = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(maximo > 0 && lotes > maximo)
      lotes = maximo;
   return lotes;
  }

string TextoLotes(const Senal &s)
  {
   string riesgo = NumeroCorto(RiesgoPct) + " %";
   double lotes = Lotes(s);
   double minimo = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   if(lotes <= 0)
      return riesgo + " = lotes sin calcular";
   if(lotes < minimo)
      return riesgo + " = menos del mínimo (" + DoubleToString(minimo, DecimalesVolumen()) + " lotes)";
   return riesgo + " = " + DoubleToString(lotes, DecimalesVolumen()) + " lotes";
  }

void Notificar(const string texto)
  {
   string corto = (StringLen(texto) > 255) ? StringSubstr(texto, 0, 252) + "..." : texto;
   if(!SendNotification(corto))
      Print("BotCRT: no se pudo enviar el aviso al móvil (¿está puesto el MetaQuotes ID?). Error ", GetLastError());
  }

void Avisar(Senal &s)
  {
   string t = "BOT CRT · " + (s.direccion > 0 ? "COMPRA " : "VENTA ") + g_mercado;
   t += " · " + (Sesion(s.hora_ny) == "Londres" ? "en Londres" : "tras la apertura");
   t += " · Entrada " + Precio(s.entrada) + " · Stop " + Precio(s.stop_inicial) + " · TP " + Precio(s.tp);
   t += " · 1 a " + NumeroCorto((s.tp - s.entrada) * s.direccion / s.riesgo) + " · " + TextoLotes(s);   // con el TP en el objetivo del 4H no es Ratio
   t += " · " + (s.escenario == 0 ? "otro escenario" : "Escenario " + IntegerToString(s.escenario));
   t += " · Nota " + Nota(s.banderas);
   if(s.banderas != 0)
      t += " (" + TextoBanderas(s.banderas) + ")";
   string noticias = NoticiasDelDia(s.hora_ny);
   if(noticias != "")
      t += " · Hoy: " + noticias;
   if(Modo == OPERAR_EN_DEMO && !PuedeOperar())
      t += " · (cuenta real: no opera)";
   Print(t);
   Alert(t);
   Notificar(t);
   s.avisada = true;
  }

void Operar(Senal &s)
  {
   if(!PuedeOperar())
      return;
   if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) == 0 || MQLInfoInteger(MQL_TRADE_ALLOWED) == 0)
     {
      Print("BotCRT: no opera porque el «Trading algorítmico» está desactivado en MT5.");
      return;
     }
   double lotes = Lotes(s);
   double minimo = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   if(lotes <= 0 || lotes < minimo)
     {
      Print("BotCRT: no opera: con este stop, el lote mínimo arriesga más del ", NumeroCorto(RiesgoPct), " %.");
      return;
     }
   double sl = NormalizeDouble(s.stop_inicial, _Digits);
   double tp = NormalizeDouble(s.tp, _Digits);
   bool ok = (s.direccion > 0) ? g_trade.Buy(lotes, _Symbol, 0.0, sl, tp, "BotCRT")
                               : g_trade.Sell(lotes, _Symbol, 0.0, sl, tp, "BotCRT");
   uint codigo = g_trade.ResultRetcode();
   if(ok && (codigo == TRADE_RETCODE_DONE || codigo == TRADE_RETCODE_PLACED))
     {
      s.ticket = g_trade.ResultOrder();
      Print("BotCRT: orden puesta (", DoubleToString(lotes, DecimalesVolumen()), " lotes).");
     }
   else
      Print("BotCRT: la orden no ha entrado: ", codigo, " ", g_trade.ResultRetcodeDescription());
  }

void MoverStopReal(const Senal &s)
  {
   if(s.ticket == 0 || !PositionSelectByTicket(s.ticket))
      return;
   if(!g_trade.PositionModify(s.ticket, NormalizeDouble(s.stop, _Digits), NormalizeDouble(s.tp, _Digits)))
      Print("BotCRT: no he podido mover el stop a la entrada: ", g_trade.ResultRetcodeDescription());
  }

void CerrarReal(const Senal &s)
  {
   if(s.ticket == 0 || !PositionSelectByTicket(s.ticket))
      return;
   if(!g_trade.PositionClose(s.ticket))
      Print("BotCRT: no he podido cerrar la posición: ", g_trade.ResultRetcodeDescription());
  }

// ───────────────────────── Operaciones (la real y las fantasma) ─────────────────────────

void Salir(Senal &s, const double precio, const int resultado, const datetime hora)
  {
   s.salida = precio;
   s.resultado = resultado;
   s.hora_salida = hora;
   s.r = (precio - s.entrada) / s.riesgo * s.direccion;
  }

double PrecioDeSalida(const Senal &s, const double cierre)
  {
   return (s.direccion > 0) ? cierre : cierre + s.dif;   // una venta se cierra comprando
  }

// ¿Toca el stop o el TP en esta barra? Igual que _revisar_salida en crt/motor.py.
bool RevisarSalida(Senal &s, const Vela &b)
  {
   double ap, mx, mn, salida_stop, a_favor, en_contra;
   bool toca_stop, toca_tp;
   datetime hora = b.inicio + SEG_M15;
   if(s.direccion > 0)
     {
      ap = b.apertura;
      mx = b.maximo;
      mn = b.minimo;
      toca_stop = mn <= s.stop;
      toca_tp = mx >= s.tp;
      salida_stop = MathMin(s.stop, ap);   // si abre más allá del stop, sale a la apertura
      a_favor = (mx - s.entrada) / s.riesgo;
      en_contra = (s.entrada - mn) / s.riesgo;
     }
   else
     {
      ap = b.apertura + s.dif;
      mx = b.maximo + s.dif;
      mn = b.minimo + s.dif;
      toca_stop = mx >= s.stop;
      toca_tp = mn <= s.tp;
      salida_stop = MathMax(s.stop, ap);
      a_favor = (s.entrada - mn) / s.riesgo;
      en_contra = (mx - s.entrada) / s.riesgo;
     }
   if(en_contra > s.mae)
      s.mae = en_contra;
   if(toca_stop)   // si en la misma barra toca también el TP, cuenta el stop
     {
      Salir(s, salida_stop, s.en_entrada ? RES_BE : RES_SL, hora);
      return true;
     }
   if(a_favor > s.mfe)
      s.mfe = a_favor;
   if(toca_tp)
     {
      Salir(s, s.tp, RES_TP, hora);
      return true;
     }
   if(StopAEntradaEnR > 0 && !s.en_entrada && s.mfe >= StopAEntradaEnR)
     {
      s.stop = s.entrada;   // vale desde la barra siguiente
      s.en_entrada = true;
      if(s.tomada && s.ticket > 0)
         MoverStopReal(s);
     }
   return false;
  }

// Una operación que se cierra: se apunta en la memoria y, si era la real, se avisa.
void Terminar(Senal &s)
  {
   if(s.apuntar)
      Apuntar(s);
   if(s.tomada && s.avisada)
     {
      string t = "BOT CRT · " + g_mercado + " · " + TextoResultado(s.resultado) + " · " + Numero(s.r) + " R";
      Print(t);
      Notificar(t);
     }
   if(s.tomada && s.ticket > 0 && s.resultado != RES_TP && s.resultado != RES_SL && s.resultado != RES_BE)
      CerrarReal(s);   // las salidas que no son el stop ni el TP de la orden se cierran a mano
  }

// La operación real se ha cerrado: se lleva la cuenta del día y de la racha de stops (crt/motor.py:
// _cerrada) y se deja en la variable global para los bots de los otros mercados.
void CuentaCerrada(const Senal &s)
  {
   long dia = DiaDeTrading(s.hora_salida - SEG_M15);
   if(dia != g_dia_r)
     {
      g_dia_r = dia;
      g_r_dia = 0;
     }
   g_r_dia += s.r;
   g_racha = (s.r < 0) ? g_racha + 1 : 0;
   if(PausaTrasStops > 0 && g_racha >= PausaTrasStops)
     {
      g_pausa_hasta = SiguienteDiaHabil(dia);
      g_racha = 0;
      if(g_en_vivo)
        {
         string t = "BOT CRT · " + g_mercado + " · " + IntegerToString(PausaTrasStops) + " stops seguidos: pausa hasta el "
                    + Fecha((datetime)(g_pausa_hasta * SEG_DIA)) + ". Descansad (vídeo de psicología).";
         Print(t);
         Notificar(t);
        }
     }
   if(dia == DiaDeTrading(AhoraNY()) && MQLInfoInteger(MQL_TESTER) == 0)
      GlobalVariableSet(VariableDelDia(dia), g_r_dia);
  }

void QuitarFantasma(const int k)
  {
   int n = ArraySize(g_fantasmas);
   for(int j = k + 1; j < n; j++)
      g_fantasmas[j - 1] = g_fantasmas[j];
   ArrayResize(g_fantasmas, n - 1);
  }

// Regla candidata de la «zona de peligro» (crt/motor.py: _peligro): ganando, si la vela de 4H y la de 1H
// en curso hacen máximos nuevos (en ventas, mínimos) y una vela de M15 barre la anterior y vuelve a
// cerrar dentro, se sale al cierre de esa vela. Devuelve true si la operación se cierra.
bool EnZonaDePeligro(Senal &s, const Vela &b)
  {
   int d = s.direccion;
   if(!SalidaPeligro || !g_hay_anterior || !(g_h4.Tomando(d) && g_h1.Tomando(d)))
      return false;
   double precio = PrecioDeSalida(s, b.cierre);
   Evento m15;
   bool hay = Evaluar(g_anterior, b, m15, 0);
   if((precio - s.entrada) * d <= 0 || !hay || m15.tipo != TIPO_RANGO || m15.direccion != -d)
      return false;
   Salir(s, precio, RES_PELIGRO, b.inicio + SEG_M15);
   return true;
  }

// Regla candidata de la salida por tiempo (crt/motor.py: _por_tiempo): ganando, si una vela de 4H que
// abrió después de la entrada supera el extremo de la anterior a favor (en compras, un máximo nuevo),
// se sale al cierre de esa barra, porque puede formar un rango al revés. Devuelve true si se cierra.
bool SalidaPorTiempoAhora(Senal &s, const Vela &b)
  {
   int d = s.direccion;
   if(!SalidaPorTiempo || !g_h4.hay_parcial || g_h4.parcial.inicio < s.hora_ny || !g_h4.Tomando(d))
      return false;
   double precio = PrecioDeSalida(s, b.cierre);
   if((precio - s.entrada) * d <= 0)
      return false;
   Salir(s, precio, RES_TIEMPO, b.inicio + SEG_M15);
   return true;
  }

// Regla candidata (crt/motor.py: _be_antes_de_las_9): ganando, stop a la entrada al cierre de la barra
// de las 8:45, porque «es muy probable que la vela de las 9 vaya a hacer el nuevo alto».
void PonerBreakEvenAntesDeLas9(Senal &s, const Vela &b)
  {
   if(!BreakEvenAntesDeLas9 || s.en_entrada || MinutosDelDia(b.inicio + SEG_M15) != VELA_DE_LAS_9_MIN)
      return;
   if((PrecioDeSalida(s, b.cierre) - s.entrada) * s.direccion <= 0)
      return;
   s.stop = s.entrada;   // vale desde la barra siguiente
   s.en_entrada = true;
   if(s.tomada && s.ticket > 0)
      MoverStopReal(s);
  }

// ¿Se cierra la operación en esta barra? Stop o TP y las salidas candidatas. Si sigue abierta y toca,
// se lleva el stop a la entrada antes de la vela de las 9 (crt/motor.py: _sale).
bool SeCierra(Senal &s, const Vela &b)
  {
   if(RevisarSalida(s, b) || EnZonaDePeligro(s, b) || SalidaPorTiempoAhora(s, b))
      return true;
   PonerBreakEvenAntesDeLas9(s, b);
   return false;
  }

void RevisarSalidas(const Vela &b)
  {
   if(g_hay_real && SeCierra(g_real, b))
     {
      Terminar(g_real);
      CuentaCerrada(g_real);
      g_hay_real = false;
     }
   for(int k = ArraySize(g_fantasmas) - 1; k >= 0; k--)
      if(SeCierra(g_fantasmas[k], b))
        {
         Terminar(g_fantasmas[k]);
         QuitarFantasma(k);
        }
  }

// Cierra lo abierto (la real y las fantasma) al precio de cierre: fin de semana, hueco en los datos o,
// con la regla candidata del cierre del día, fin del día.
void CerrarTodo(const double cierre, const datetime hora, const int resultado)
  {
   if(g_hay_real)
     {
      Salir(g_real, PrecioDeSalida(g_real, cierre), resultado, hora);
      Terminar(g_real);
      CuentaCerrada(g_real);
      g_hay_real = false;
     }
   for(int k = 0; k < ArraySize(g_fantasmas); k++)
     {
      Salir(g_fantasmas[k], PrecioDeSalida(g_fantasmas[k], cierre), resultado, hora);
      Terminar(g_fantasmas[k]);
     }
   ArrayResize(g_fantasmas, 0);
  }

// En vivo, la barra que acaba a las 17:00 se procesa cuando llega la siguiente, y en NASDAQ y oro eso es
// a las 18:00, tras el parón (el viernes, el domingo). Para que la posición de la cuenta no se quede
// abierta durante el parón, se cierra unos minutos antes: el viernes siempre y, con la regla del cierre
// del día, cada día. La memoria la apunta igual, al cierre de la barra, como el Python.
void CerrarAntesDelParon(void)
  {
   if(!g_listo || !g_hay_real || g_real.ticket == 0)
      return;
   datetime ahora = AhoraNY();
   int m = MinutosDelDia(ahora);
   if(m < FIN_DEL_DIA_MIN - MINUTOS_ANTES_DEL_PARON || m >= FIN_DEL_DIA_MIN)
      return;
   MqlDateTime st;
   TimeToStruct(ahora, st);
   if(st.day_of_week != 5 && !CierreDiario)
      return;
   CerrarReal(g_real);
   if(!PositionSelectByTicket(g_real.ticket))
     {
      Print("BotCRT: posición cerrada antes del cierre de las 17:00 de Nueva York.");
      g_real.ticket = 0;
     }
  }

// Regla candidata: un rango de 1H en contra cierra la operación o, si va ganando y así se ha elegido,
// le lleva el stop a la entrada. Devuelve true si la operación se cierra (crt/motor.py: _salida_1h).
bool SalidaPor1H(Senal &s, const datetime hora, const double cierre)
  {
   double precio = PrecioDeSalida(s, cierre);
   if(Salida1H == SALIDA_ENTRADA && (precio - s.entrada) * s.direccion > 0)
     {
      if(!s.en_entrada)
        {
         s.stop = s.entrada;   // vale desde la barra siguiente
         s.en_entrada = true;
         if(s.tomada && s.ticket > 0)
            MoverStopReal(s);
        }
      return false;
     }
   Salir(s, precio, RES_1H, hora);
   return true;
  }

// Cierra la vela de 1H y, con la regla de salida por 1H, mira si ha formado un rango en contra de lo
// que está abierto (crt/motor.py: _cerrar).
void CerrarH1(const datetime hora, const double cierre)
  {
   if(!g_h1.Cerrar() || Salida1H == SALIDA_NO)
      return;
   Evento e;
   g_h1.UltimoEvento(e);
   if(e.tipo != TIPO_RANGO)
      return;
   if(g_hay_real && e.direccion == -g_real.direccion && SalidaPor1H(g_real, hora, cierre))
     {
      Terminar(g_real);
      CuentaCerrada(g_real);
      g_hay_real = false;
     }
   for(int k = ArraySize(g_fantasmas) - 1; k >= 0; k--)
      if(e.direccion == -g_fantasmas[k].direccion && SalidaPor1H(g_fantasmas[k], hora, cierre))
        {
         Terminar(g_fantasmas[k]);
         QuitarFantasma(k);
        }
  }

// ───────────────────────── Decisión ─────────────────────────

// Entrada, stop, riesgo y TP, o el motivo por el que no se pueden poner (DEC_NINGUNA si se puede).
int Niveles(const int d, const double precio, const Setup &s, const double dif,
            double &entrada, double &stop, double &riesgo, double &tp)
  {
   double colchon = ColchonStopPuntos * _Point;
   if(d > 0)
     {
      if(precio <= s.barrido)
         return DEC_BARRIDO;
      entrada = precio + dif;                  // se compra al precio de compra
      stop = s.barrido - colchon;
      riesgo = entrada - stop;
     }
   else
     {
      if(precio >= s.barrido)
         return DEC_BARRIDO;
      entrada = precio;
      stop = s.barrido + colchon + dif;        // las ventas se cierran comprando
      riesgo = stop - entrada;
     }
   if(riesgo <= 0 || riesgo < STOP_MINIMO_EN_DIFERENCIALES * dif)
      return DEC_STOP_CORTO;
   double objetivo_4h = (d > 0) ? s.objetivo : s.objetivo + dif;
   if(!TpEnObjetivo4H)
     {
      tp = entrada + d * Ratio * riesgo;
      if(TpHastaObjetivo4H && (objetivo_4h - tp) * d > 0)
         tp = objetivo_4h;   // regla candidata: «al menos ratio 2… o el objetivo», si el del 4H está más lejos
      return DEC_NINGUNA;
     }
   // Regla candidata: el TP en el objetivo del rango de 4H («en fondeo solo voy a por los primeros objetivos»).
   tp = objetivo_4h;
   if((tp - entrada) * d < MINIMO_R_OBJETIVO * riesgo)
      return DEC_OBJETIVO;
   return DEC_NINGUNA;
  }

bool Cabe(const int d, const double tp, const double objetivo, const double dif)
  {
   if(objetivo == VACIO)
      return true;
   return (d > 0) ? tp <= objetivo : tp >= objetivo + dif;
  }

// Las banderas rojas de esta situación (crt/motor.py: _banderas).
int Banderas(const int d, const datetime hora, const double precio, const int c3, const int c1, const bool hay_niveles,
             const double riesgo)
  {
   int b = 0;
   if(g_d1.SemaforoCerrado(d) == -1)
      b |= BAN_DIARIO_EN_CONTRA;
   if(g_d1.Tomando(d))
      b |= (d > 0) ? BAN_DIARIO_MAXIMOS : BAN_DIARIO_MINIMOS;
   if(g_h4.Tomando(d))
      b |= (d > 0) ? BAN_4H_MAXIMOS : BAN_4H_MINIMOS;
   if(g_h1.Tomando(d))
      b |= (d > 0) ? BAN_1H_MAXIMOS : BAN_1H_MINIMOS;
   if(c3 == -1)
      b |= BAN_3H_EN_CONTRA;
   if(c1 == -1)
      b |= BAN_1H_EN_CONTRA;
   if(g_d1.hay_parcial && (precio - g_d1.parcial.apertura) * d > 0)
      b |= (d > 0) ? BAN_APERTURA_COMPRA : BAN_APERTURA_VENTA;
   int m = MinutosDelDia(hora);
   if(APERTURA_NY_MIN - 30 < m && m <= APERTURA_NY_MIN)
      b |= BAN_ANTES_APERTURA;
   double medio = g_h4.RangoMedio();
   if(hay_niveles && medio != VACIO && medio != 0 && riesgo > medio)
      b |= BAN_LEJOS;
   return b;
  }

// Reglas candidatas, pausa y topes del día (crt/motor.py: _filtros), en el mismo orden.
int Filtros(const Setup &s, const datetime hora, const Vela &b, const int c3, const int c1, const int banderas)
  {
   long dia = DiaDeTrading(b.inicio);
   if(!g_esc_ok[s.escenario])
      return DEC_ESCENARIO;
   if(Vela1Minima > 0 && (s.vela1_rel == VACIO || s.vela1_rel < Vela1Minima))
      return DEC_VELA1;
   if(SinNoticias && NoticiasDelDia(hora) != "")
      return DEC_NOTICIAS;
   if(AntesDeNoticias)
     {
      int primera = PrimeraHoraDeNoticias(NoticiasDelDia(hora));
      if(primera >= 0 && MinutosDelDia(hora) <= primera)
         return DEC_ANTES_NOTICIAS;   // «el precio no tiene por qué llegar a ningún sitio si va a llegar con la noticia»
     }
   if(Exigir3H != EXIGIR_NADA && !Acompana(c3, Exigir3H))
      return DEC_H3;
   if(Exigir1H != EXIGIR_NADA && !Acompana(c1, Exigir1H))
      return DEC_H1;
   if(SoloSinBanderas && banderas != 0)
      return DEC_BANDERAS;
   if(VetarTomando && (banderas & (BAN_DIARIO_MAXIMOS | BAN_DIARIO_MINIMOS | BAN_4H_MAXIMOS | BAN_4H_MINIMOS)) != 0)
      return DEC_BANDERAS;   // «nunca estar vendiendo tras tomar bajos»
   if(SoloLadoDeLaApertura && (banderas & (BAN_APERTURA_COMPRA | BAN_APERTURA_VENTA)) != 0)
      return DEC_APERTURA;
   if(g_pausa_hasta >= 0 && dia <= g_pausa_hasta)
      return DEC_PAUSA;
   if(PerdidaMaxDiaR > 0 && ResultadoDelDia(dia) <= -PerdidaMaxDiaR)
      return DEC_PERDIDA;
   if(OperacionesDelDia(dia) >= MaxOperacionesDia)
      return DEC_TOPE;
   return DEC_NINGUNA;
  }

// Al cierre de una barra, para una dirección: si hay order block con el 4H a favor, comprueba todo
// lo demás y decide. Igual que _mirar en crt/motor.py, en el mismo orden.
void Mirar(const Vela &b, const int d)
  {
   datetime hora = b.inicio + SEG_M15;      // se entra al cierre de la barra
   if(!HoraPermitida(hora))
      return;
   if(!EsOrderBlock(g_anterior, b, d))
      return;
   double precio = b.cierre;
   Setup s;
   if(!g_h4.DameSetup(d, precio, s))
      return;
   // La idea de 4H ya dio su entrada. Si la vela en curso está formando otro rango a favor (por
   // ejemplo, tras barrer el stop), es una idea nueva: volver a entrar tras un stop.
   if(s.via == VIA_CIERRE && IdeaEn(g_usadas, s) && !g_h4.DameAnticipo(d, precio, s))
      return;
   if(b.i_fin <= s.i_inicio)
      return;
   if(IdeaEn(g_usadas, s))
      return;                               // esta idea ya dio su entrada: no hay nada nuevo

   // El diario: su color, si está a favor y dónde está su objetivo.
   Setup sd;
   bool hay_diario = g_d1.DameSetup(d, precio, sd);
   int color_diario = hay_diario ? 1 : g_d1.SemaforoCerrado(d);
   double objetivo = hay_diario ? sd.objetivo : VACIO;
   bool diario_vale = hay_diario || IgnorarDiario;
   bool vale_sin_rango = (DiarioBastaNoRojo && color_diario != -1) || (DiarioValeExpansiva && g_d1.UltimaEsRuptura(d));
   if(!hay_diario && g_d1.NCerradas() > 0 && vale_sin_rango)
     {
      // Tras una vela diaria expansiva, «es muy probable que vayamos a tomar el máximo del día anterior».
      Vela previa;
      g_d1.UltimaCerrada(previa);
      objetivo = (d > 0) ? previa.maximo : previa.minimo;
      diario_vale = true;
     }
   if(IgnorarDiario)
      objetivo = VACIO;

   double entrada = 0, stop = 0, riesgo = 0, tp = 0;
   int motivo_niveles = Niveles(d, precio, s, b.dif, entrada, stop, riesgo, tp);
   int c3 = g_h3.ColorSemaforo(d, precio);
   int c1 = g_h1.ColorSemaforo(d, precio);
   int banderas = Banderas(d, hora, precio, c3, c1, motivo_niveles == DEC_NINGUNA, riesgo);

   int decision;
   if(!IgnorarSesgo && SesgoDeFondo() != d)
      decision = DEC_SIN_SESGO;
   else
      if(!diario_vale)
         decision = DEC_DIARIO;
      else
         if(g_hay_real)
            decision = DEC_ABIERTA;
         else
            if(NoPerseguir && (banderas & BAN_LEJOS) != 0)
               decision = DEC_LEJOS;         // «nunca entréis persiguiendo el precio»: la idea no se gasta
            else
              {
               MarcarIdea(g_usadas, s);      // solo cuenta el primer order block de cada idea
               decision = Filtros(s, hora, b, c3, c1, banderas);
               if(decision == DEC_NINGUNA)
                 {
                  if(motivo_niveles != DEC_NINGUNA)
                     decision = motivo_niveles;
                  else
                     if(ComprobarObjetivo4H && !Cabe(d, tp, s.objetivo, b.dif))
                        decision = DEC_NO_CABE_4H;   // «no vamos a querer tomar un trade de ratio uno»
                     else
                        if(ComprobarObjetivoDiario && !Cabe(d, tp, objetivo, b.dif))
                           decision = DEC_NO_CABE;
                        else
                           decision = DEC_ENTRADA;
                 }
              }

   bool nueva = !IdeaEn(g_vistas, s);
   MarcarIdea(g_vistas, s);
   if(!nueva && decision != DEC_ENTRADA)
      return;

   Senal sen;
   ZeroMemory(sen);
   sen.hora_ny = hora;
   sen.direccion = d;
   sen.decision = decision;
   sen.sesgo_sem = g_w1.DireccionUltimo() * d;
   sen.sesgo_men = g_mn.DireccionUltimo() * d;
   sen.diario = color_diario;
   sen.via_diario = hay_diario ? sd.via : VIA_NINGUNA;
   sen.via_4h = s.via;
   sen.h3 = c3;
   sen.h1 = c1;
   sen.banderas = banderas;
   sen.escenario = s.escenario;
   sen.vela1_rel = s.vela1_rel;
   sen.stop_rel = VACIO;
   sen.objetivo_r = VACIO;
   sen.apuntar = g_en_vivo || EscribirMemoriaHistorica;
   sen.hay_op = (motivo_niveles == DEC_NINGUNA);
   if(sen.hay_op)
     {
      double medio = g_h4.RangoMedio();
      sen.tomada = (decision == DEC_ENTRADA);
      sen.entrada = entrada;
      sen.stop = stop;
      sen.stop_inicial = stop;
      sen.tp = tp;
      sen.riesgo = riesgo;
      sen.dif = b.dif;
      if(medio != VACIO && medio != 0)
         sen.stop_rel = riesgo / medio;
      if(objetivo != VACIO)
         sen.objetivo_r = (objetivo - entrada) * d / riesgo;
     }
   if(g_en_vivo)
      g_ultima_senal = FechaHora(hora) + " · " + (d > 0 ? "compra" : "venta") + " · " + TextoDecision(decision);

   if(decision == DEC_ENTRADA)
     {
      g_real = sen;
      g_hay_real = true;
      SumarOperacionDelDia(DiaDeTrading(b.inicio));
      if(g_en_vivo)
        {
         if(g_tardia)
            Print("BotCRT: señal de las ", FechaHora(hora), " procesada con retraso: no se avisa ni se opera.");
         else
           {
            Avisar(g_real);
            Operar(g_real);
           }
        }
     }
   else
      if(sen.hay_op)
        {
         int n = ArraySize(g_fantasmas);
         ArrayResize(g_fantasmas, n + 1);
         g_fantasmas[n] = sen;
        }
      else
         if(sen.apuntar)
            Apuntar(sen);   // sin niveles no hay nada que seguir: se apunta ya
  }

// ───────────────────────── Barra a barra ─────────────────────────

// Una barra de M15 cerrada, en el mismo orden que _Recorrido.paso en crt/motor.py.
void ProcesarBarra(Vela &b)
  {
   // 1. Una semana nueva sin que la anterior cerrara en los datos: se cierra lo abierto donde se
   //    quedó el precio, y se cierran las velas que había.
   if(g_hay_anterior && g_w1.TocaCerrarAntes(b))
      CerrarTodo(g_anterior.cierre, g_anterior.inicio + SEG_M15, RES_SEMANAL);
   if(g_hay_anterior && CierreDiario && g_d1.TocaCerrarAntes(b))
      CerrarTodo(g_anterior.cierre, g_anterior.inicio + SEG_M15, RES_DIA);
   if(g_h1.TocaCerrarAntes(b))
      CerrarH1(g_anterior.inicio + SEG_M15, g_anterior.cierre);
   if(g_h3.TocaCerrarAntes(b))
      g_h3.Cerrar();
   if(g_h4.TocaCerrarAntes(b))
      g_h4.Cerrar();
   if(g_d1.TocaCerrarAntes(b))
      g_d1.Cerrar();
   if(g_w1.TocaCerrarAntes(b))
      g_w1.Cerrar();
   if(g_mn.TocaCerrarAntes(b))
      g_mn.Cerrar();

   // 2. ¿Algún rango ha llegado a su objetivo? Y se suma la barra a las velas en curso.
   g_h1.ActualizarConBarra(b);
   g_h1.Sumar(b);
   g_h3.ActualizarConBarra(b);
   g_h3.Sumar(b);
   g_h4.ActualizarConBarra(b);
   g_h4.Sumar(b);
   g_d1.ActualizarConBarra(b);
   g_d1.Sumar(b);
   g_w1.ActualizarConBarra(b);
   g_w1.Sumar(b);
   g_mn.ActualizarConBarra(b);
   g_mn.Sumar(b);

   // 3. Las operaciones abiertas: ¿tocan el stop o el TP? ¿Alguna salida candidata?
   RevisarSalidas(b);

   // 4. Se cierran las velas que terminan con esta barra (con la salida por 1H, un rango de 1H en
   //    contra cierra lo abierto). El viernes a las 17:00 se cierra todo (con la regla del cierre del
   //    día, cada día).
   datetime hora = b.inicio + SEG_M15;
   bool fin_de_semana = g_w1.TocaCerrarDespues(b);
   bool fin_del_dia = g_d1.TocaCerrarDespues(b);
   if(g_h1.TocaCerrarDespues(b))
      CerrarH1(hora, b.cierre);
   if(g_h3.TocaCerrarDespues(b))
      g_h3.Cerrar();
   if(g_h4.TocaCerrarDespues(b))
      g_h4.Cerrar();
   if(g_d1.TocaCerrarDespues(b))
      g_d1.Cerrar();
   if(g_w1.TocaCerrarDespues(b))
      g_w1.Cerrar();
   if(g_mn.TocaCerrarDespues(b))
      g_mn.Cerrar();
   if(fin_de_semana)
      CerrarTodo(b.cierre, hora, RES_SEMANAL);
   else
      if(fin_del_dia && CierreDiario)
         CerrarTodo(b.cierre, hora, RES_DIA);

   // 5. Al cierre de la barra, para compras y para ventas.
   if(g_hay_anterior && !fin_de_semana)
     {
      Mirar(b, 1);
      Mirar(b, -1);
     }
   g_anterior = b;
   g_hay_anterior = true;
  }

double Diferencial(const MqlRates &r, const bool ahora)
  {
   if(DiferencialFijoPuntos > 0)
      return DiferencialFijoPuntos * _Point;
   if(ahora)
     {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if(ask > 0 && bid > 0 && ask >= bid)
         return ask - bid;
     }
   if(r.spread > 0)
      return r.spread * _Point;
   return (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
  }

void ProcesarRates(const MqlRates &r, const bool en_vivo, const bool tardia)
  {
   Vela b;
   b.inicio = (datetime)((long)r.time - (long)DesfaseServidorNY * SEG_HORA);
   b.apertura = r.open;
   b.maximo = r.high;
   b.minimo = r.low;
   b.cierre = r.close;
   b.i_inicio = g_i;
   b.i_fin = g_i;
   g_i++;
   b.dif = Diferencial(r, en_vivo && !tardia);
   g_en_vivo = en_vivo;
   g_tardia = tardia;
   ProcesarBarra(b);
  }

// Al arrancar: la historia, para tener el estado (sin avisar ni operar).
bool CargarHistoria(void)
  {
   datetime abierta = iTime(_Symbol, PERIOD_M15, 0);   // la barra en curso, que no se procesa
   if(abierta == 0)
      return false;
   datetime desde = (datetime)((long)abierta - (long)MesesHistoria * 31 * SEG_DIA);
   MqlRates barras[];
   int n = CopyRates(_Symbol, PERIOD_M15, desde, abierta, barras);
   if(n <= 0)
     {
      Print("BotCRT: esperando a que MT5 cargue la historia de ", _Symbol, " (error ", GetLastError(), ").");
      return false;
     }
   int procesadas = 0;
   for(int k = 0; k < n; k++)
     {
      if(barras[k].time >= abierta)
         break;
      ProcesarRates(barras[k], false, false);
      g_ultima_barra = barras[k].time;
      procesadas++;
     }
   g_en_vivo = true;
   Print("BotCRT: ", procesadas, " barras de 15 minutos de historia procesadas (desde ", TimeToString(desde, TIME_DATE), ").");
   return procesadas > 0;
  }

// Procesa las barras de 15 minutos que se hayan cerrado desde la última vez.
void RevisarBarrasNuevas(void)
  {
   if(!g_listo)
     {
      g_listo = CargarHistoria();
      if(!g_listo)
         return;
     }
   datetime abierta = iTime(_Symbol, PERIOD_M15, 0);
   if(abierta == 0 || abierta <= g_ultima_barra + SEG_M15)
      return;
   MqlRates nuevas[];
   int n = CopyRates(_Symbol, PERIOD_M15, g_ultima_barra + SEG_M15, abierta, nuevas);
   if(n <= 0)
      return;
   for(int k = 0; k < n; k++)
     {
      if(nuevas[k].time <= g_ultima_barra || nuevas[k].time >= abierta)
         continue;
      long retraso = (long)TimeCurrent() - ((long)nuevas[k].time + SEG_M15);
      ProcesarRates(nuevas[k], true, retraso > MINUTOS_TARDE * 60);
      g_ultima_barra = nuevas[k].time;
     }
   AvisoDeTope();
   ActualizarPanel();
  }

// ───────────────────────── Panel ─────────────────────────

string TextoModo(void)
  {
   if(Modo == SOLO_AVISOS)
      return "solo avisa";
   if(PuedeOperar())
      return EsCuentaDemo() ? "opera en DEMO" : "¡OPERA EN CUENTA REAL!";
   return "solo avisa (cuenta real)";
  }

string TextoAhora(void)
  {
   datetime ahora = AhoraNY();
   int m = MinutosDelDia(ahora);
   string hora = HoraMin(ahora) + " en Nueva York";
   if(HoraPermitida(ahora))
      return "se puede entrar (" + hora + ")";
   if(EsperaAperturaMin > 0 && APERTURA_NY_MIN < m && m < APERTURA_NY_MIN + EsperaAperturaMin)
      return "espera tras la apertura (" + hora + ")";
   return "fuera de horario (" + hora + ")";
  }

string TextoOperacion(void)
  {
   if(!g_hay_real)
      return "ninguna";
   string t = (g_real.direccion > 0 ? "compra" : "venta") + " en " + Precio(g_real.entrada);
   t += " · stop " + Precio(g_real.stop) + " · TP " + Precio(g_real.tp);
   if(!g_real.apuntar)
      t += " (de la historia, sin aviso)";
   if(g_real.ticket > 0)
      t += " · en la cuenta";
   return t;
  }

// Lo que lleva hoy este mercado y, con el tope, todos los mercados (vídeo de psicología: bloqueadores).
string TextoHoy(void)
  {
   long hoy = DiaDeTrading(AhoraNY());
   string t = NumeroR(hoy == g_dia_r ? g_r_dia : 0.0) + " en este mercado";
   if(PerdidaMaxDiaR <= 0)
      return t;
   double todos = ResultadoDelDia(hoy);
   t += " · " + NumeroR(todos) + " entre todos (tope: -" + NumeroCorto(PerdidaMaxDiaR) + " R)";
   if(todos <= -PerdidaMaxDiaR)
      t += " · TOPE ALCANZADO: hoy no entra más";
   return t;
  }

string TextoRacha(void)
  {
   if(g_pausa_hasta >= 0 && DiaDeTrading(AhoraNY()) <= g_pausa_hasta)
      return "en pausa hasta el " + Fecha((datetime)(g_pausa_hasta * SEG_DIA)) + " (regla de la pausa tras stops)";
   string t = IntegerToString(g_racha) + (g_racha == 1 ? " stop seguido" : " stops seguidos");
   if(g_racha >= 3)
      t += " · Consejo del vídeo de psicología: tras una racha así, parad un día";
   return t;
  }

// Avisa una sola vez al día, desde uno solo de los bots, de que se ha llegado al tope de pérdida.
void AvisoDeTope(void)
  {
   if(PerdidaMaxDiaR <= 0 || MQLInfoInteger(MQL_TESTER) != 0)
      return;
   long hoy = DiaDeTrading(AhoraNY());
   if(hoy == g_dia_aviso_tope)
      return;
   double r = ResultadoDelDia(hoy);
   if(r > -PerdidaMaxDiaR)
      return;
   g_dia_aviso_tope = hoy;
   string nombre = "BotCRT.AvisoTope." + IntegerToString(hoy);
   if(!GlobalVariableCheck(nombre))
      GlobalVariableSet(nombre, 0);
   if(!GlobalVariableSetOnCondition(nombre, 1, 0))
      return;                                 // ya avisó otro de los bots
   string t = "BOT CRT · Tope de pérdida del día: " + NumeroR(r) + " entre los mercados. Hoy ya no avisa de más entradas. "
              + "Cerrad el gráfico y descansad: mañana, más.";
   Print(t);
   Notificar(t);
  }

void ActualizarPanel(void)
  {
   if(!g_listo)
     {
      Comment("BOT CRT · " + g_mercado + "\nCargando la historia de MT5...");
      return;
     }
   double precio = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   int sesgo = SesgoDeFondo();
   string sesgo_texto = (sesgo > 0) ? "COMPRAS" : ((sesgo < 0) ? "VENTAS" : "sin sesgo (no entra)");
   string t = "BOT CRT · " + g_mercado + " · " + TextoModo() + "\n";
   t += "Sesgo de fondo: " + sesgo_texto + "   (semanal: " + TextoDireccion(g_w1.DireccionUltimo())
        + " · mensual: " + TextoDireccion(g_mn.DireccionUltimo()) + ")\n";
   if(SesgoDeLaSemana != SESGO_DEL_BOT)
      t += "   Puesto por vosotros. El bot calcula: " + TextoDireccion(SesgoDelBot()) + "\n";
   t += "Diario:  compras " + TextoColor(g_d1.ColorSemaforo(1, precio)) + " · ventas " + TextoColor(g_d1.ColorSemaforo(-1, precio)) + "\n";
   t += "4H:      compras " + TextoColor(g_h4.ColorSemaforo(1, precio)) + " · ventas " + TextoColor(g_h4.ColorSemaforo(-1, precio)) + "\n";
   t += "3H:      compras " + TextoColor(g_h3.ColorSemaforo(1, precio)) + " · ventas " + TextoColor(g_h3.ColorSemaforo(-1, precio)) + "\n";
   t += "1H:      compras " + TextoColor(g_h1.ColorSemaforo(1, precio)) + " · ventas " + TextoColor(g_h1.ColorSemaforo(-1, precio)) + "\n";
   t += "Ahora:   " + TextoAhora() + "\n";
   t += "Hoy:     " + TextoHoy() + "\n";
   t += "Racha:   " + TextoRacha() + "\n";
   t += "Operación: " + TextoOperacion() + "\n";
   t += "Fantasmas siguiéndose: " + IntegerToString(ArraySize(g_fantasmas)) + "\n";
   t += "Última señal: " + (g_ultima_senal == "" ? "ninguna desde que arrancó" : g_ultima_senal);
   Comment(t);
  }

// ───────────────────────── Arranque ─────────────────────────

void Reiniciar(void)
  {
   // Al cambiar un parámetro, MT5 vuelve a llamar a OnInit sin borrar las variables: se limpia todo.
   g_siguiente_id = 0;
   g_h1.Iniciar("H1", MARCO_H1, NULL);
   g_h3.Iniciar("H3", MARCO_H3, NULL);
   g_h4.Iniciar("H4", MARCO_H4, GetPointer(g_h1), HoraInicio4H);
   g_d1.Iniciar("D1", MARCO_D1, GetPointer(g_h4), 17, ToleranciaDiario);
   g_w1.Iniciar("W1", MARCO_W1, NULL);
   g_mn.Iniciar("MN", MARCO_MN, NULL);
   ZeroMemory(g_anterior);
   g_hay_anterior = false;
   g_i = 0;
   g_hay_real = false;
   ZeroMemory(g_real);
   ArrayResize(g_fantasmas, 0);
   ArrayResize(g_usadas, 0);
   ArrayResize(g_vistas, 0);
   g_dia_ops = -1;
   g_ops_dia = 0;
   g_dia_r = -1;
   g_r_dia = 0;
   g_racha = 0;
   g_pausa_hasta = -1;
   g_dia_aviso_tope = -1;
   g_listo = false;
   g_ultima_barra = 0;
   g_en_vivo = false;
   g_tardia = false;
   g_ultima_senal = "";
   ArrayResize(g_not_dia, 0);
   ArrayResize(g_not_texto, 0);
  }

void AvisoDeCuenta(void)
  {
   if(Modo != OPERAR_EN_DEMO || EsCuentaDemo())
      return;
   if(PermitirCuentaReal)
     {
      string t = "BotCRT: ¡ATENCIÓN! Está activado operar en una CUENTA REAL. Si no es lo que queréis, quitad el bot ya.";
      Print(t);
      Print(t);
      Print(t);
      Alert(t);
     }
   else
      Print("BotCRT: esta cuenta no es demo, así que el bot no operará: solo avisa.");
  }

int OnInit(void)
  {
   Reiniciar();
   g_desde_min = LeerHora(HoraDesde);
   g_hasta_min = LeerHora(HoraHasta);
   if(g_desde_min < 0 || g_hasta_min < 0)
     {
      Alert("BotCRT: las horas tienen que ir así: 01:00, 13:00.");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(Ratio <= 0 || RiesgoPct <= 0 || MaxOperacionesDia < 0 || MesesHistoria < 2 || ColchonStopPuntos < 0)
     {
      Alert("BotCRT: revisad los parámetros (ratio, riesgo, máximo de operaciones, meses de historia o colchón).");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(HoraInicio4H < 0 || HoraInicio4H > 23 || PerdidaMaxDiaR < 0 || PausaTrasStops < 0 || ToleranciaDiario < 0 || ToleranciaDiario >= 1)
     {
      Alert("BotCRT: revisad los parámetros (hora de las velas de 4H, tope de pérdida, pausa o tolerancia del diario).");
      return INIT_PARAMETERS_INCORRECT;
     }
   LeerEscenarios();
   g_mercado = (NombreMercado != "") ? NombreMercado : _Symbol;
   g_ruta_memoria = "BotCRT\\memoria_" + NombreDeArchivo(g_mercado) + ".csv";
   FolderCreate("BotCRT");
   if(EscribirMemoriaHistorica)
      FileDelete(g_ruta_memoria);   // la historia se vuelve a escribir entera
   g_trade.SetExpertMagicNumber((ulong)NumeroMagico);
   AvisoDeCuenta();
   if(ExportarNoticias)
      ExportarNoticiasCsv();
   g_listo = CargarHistoria();
   EventSetTimer(5);
   ActualizarPanel();
   Print("BotCRT: arrancado en ", _Symbol, ". Memoria en MQL5/Files/", g_ruta_memoria);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
  }

void OnTimer(void)
  {
   RevisarBarrasNuevas();
   CerrarAntesDelParon();
   ActualizarPanel();
  }

void OnTick(void)
  {
   RevisarBarrasNuevas();
  }
//+------------------------------------------------------------------+
