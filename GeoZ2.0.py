import pygame
import random
import pickle
import sys

# ------------------------- ENTIDADES Y MECÁNICAS -------------------------
class Recurso:
    def __init__(self, tipo: str, cantidad: int, posicion_x: int, posicion_y: int):
        self.tipo = tipo
        self.cantidad = cantidad
        self.posicion_x = posicion_x
        self.posicion_y = posicion_y


class Personaje:
    def __init__(self, vida: int, ataque: int, defensa: float, velocidad: float, categoria: str, habilidad: str,
                 estado: bool, posicion_x: int, posicion_y: int, con_vida: bool = True):
        self.vida = vida
        self.ataque = ataque
        self.defensa = defensa
        self.velocidad = velocidad
        self.categoria = categoria
        self.habilidad = habilidad
        self.estado = estado
        self.con_vida = con_vida
        self.posicion_x = posicion_x
        self.posicion_y = posicion_y
        self.efectos = {}
        self.inventario = []

    def mover_aleatorio(self, escenario):
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        nuevo_x = self.posicion_x + dx
        nuevo_y = self.posicion_y + dy

        if 0 <= nuevo_x < escenario.ancho and 0 <= nuevo_y < escenario.alto:
            try:
                escenario.tablero[self.posicion_x][self.posicion_y].entidades.remove(self)
            except ValueError:
                pass
            self.posicion_x = nuevo_x
            self.posicion_y = nuevo_y
            escenario.tablero[nuevo_x][nuevo_y].entidades.append(self)

    def actuar(self, escenario):
        pass


# ------------------------- CIVILES -------------------------
class Civil(Personaje):
    def __init__(self, vida: int, ataque: int, defensa: float, velocidad: float, categoria: str, habilidad: str,
                 estado: bool, energia: int, posicion_x: int, posicion_y: int, con_vida: bool = True):
        super().__init__(vida, ataque, defensa, velocidad, categoria, habilidad, estado, posicion_x, posicion_y,
                         con_vida)
        self.energia = energia
        self.turnos_infeccion = None

    def infectar(self):
        if not self.estado and self.con_vida:
            self.estado = True
            self.turnos_infeccion = 3

    def morir(self):
        self.con_vida = False
        self.estado = False
        self.turnos_infeccion = None

    def avanzar_turno(self):
        if self.estado and self.turnos_infeccion is not None:
            self.turnos_infeccion -= 1
            if self.turnos_infeccion <= 0:
                self.morir()

        for efecto in list(self.efectos.keys()):
            self.efectos[efecto] -= 1
            if self.efectos[efecto] <= 0:
                del self.efectos[efecto]


class Civil_Normal(Civil):
    def __init__(self, vida: int = 100, ataque: int = 5, defensa: float = None, velocidad: float = 2.5,
                 categoria: str = "Civil Normal", habilidad: str = "Sobrevivir", estado: bool = False,
                 energia: int = 50, posicion_x: int = 0, posicion_y: int = 0, con_vida: bool = True):
        if defensa is None:
            defensa = vida * 0.1
        super().__init__(vida, ataque, defensa, velocidad, categoria, habilidad, estado, energia, posicion_x,
                         posicion_y, con_vida)
        self.inventario = []

    def actuar(self, escenario):
        if not self.con_vida:
            return
        self.mover_aleatorio(escenario)
        self.avanzar_turno()


class Atacante(Civil):
    def __init__(self, vida: int = 100, ataque: int = 40, defensa: float = None, velocidad: float = 5.0,
                 categoria: str = "Atacante", habilidad: str = "Esquivar", estado: bool = False,
                 energia: int = 100, posicion_x: int = 0, posicion_y: int = 0, con_vida: bool = True):
        if defensa is None:
            defensa = vida * 0.2
        super().__init__(vida, ataque, defensa, velocidad, categoria, habilidad, estado, energia, posicion_x,
                         posicion_y, con_vida)
        self.inventario = ["Espada"]

    def esquivar(self):
        self.efectos["esquivando"] = 5

    def mover_hacia_zombi(self, escenario):
        # comportamiento simple: moverse aleatoriamente
        self.mover_aleatorio(escenario)

    def atacar(self, escenario):
        x = self.posicion_x
        y = self.posicion_y
        celda = escenario.tablero[x][y]
        for entidad in list(celda.entidades):
            if isinstance(entidad, Zombie) and entidad.con_vida:
                daño = max(0, int(self.ataque - entidad.defensa))
                entidad.vida -= daño
                killed = False
                if entidad.vida <= 0:
                    entidad.con_vida = False
                    try:
                        celda.entidades.remove(entidad)
                    except ValueError:
                        pass
                    if entidad in escenario.personajes:
                        escenario.personajes.remove(entidad)
                    killed = True
                return (entidad.__class__.__name__, daño, killed, (x, y))
        return None

    def actuar(self, escenario):
        if not self.con_vida:
            return
        resultado = self.atacar(escenario)
        self.mover_hacia_zombi(escenario)
        self.avanzar_turno()
        return resultado


class Defensor(Civil):
    def __init__(self, vida: int = 100, ataque: int = 20, defensa: float = None, velocidad: float = 3.5,
                 categoria: str = "Defensor", habilidad: str = "Bloqueo", estado: bool = False,
                 energia: int = 100, posicion_x: int = 0, posicion_y: int = 0, con_vida: bool = True):
        if defensa is None:
            defensa = vida * 0.5
        super().__init__(vida, ataque, defensa, velocidad, categoria, habilidad, estado, energia, posicion_x,
                         posicion_y, con_vida)
        self.inventario = ["Escudo"]

    def bloquear(self):
        self.efectos["bloqueando"] = 8

    def mover_hacia_civil(self, escenario):
        self.mover_aleatorio(escenario)

    def proteger(self, civil: Civil):
        if civil.con_vida:
            civil.efectos["protegido"] = 3
            return civil
        return None

    def actuar(self, escenario):
        if not self.con_vida:
            return
        self.mover_hacia_civil(escenario)
        x, y = self.posicion_x, self.posicion_y
        celda = escenario.tablero[x][y]
        for entidad in celda.entidades:
            if isinstance(entidad, Civil) and entidad.con_vida and entidad != self:
                self.proteger(entidad)
                break
        self.avanzar_turno()


class Productor(Civil):
    def __init__(self, vida: int = 100, ataque: int = 5, defensa: float = None, velocidad: float = 4.0,
                 categoria: str = "Productor", habilidad: str = "Duplicar", estado: bool = False,
                 energia: int = 150, posicion_x: int = 0, posicion_y: int = 0, con_vida: bool = True):
        if defensa is None:
            defensa = vida * 0.1
        super().__init__(vida, ataque, defensa, velocidad, categoria, habilidad, estado, energia, posicion_x,
                         posicion_y, con_vida)
        self.inventario = ["Saco"]

    def recolectar(self, recurso: Recurso):
        if recurso.cantidad > 0:
            cantidad = 1
            if self.efectos.get("recolectando_doble", 0) > 0:
                cantidad *= 2
            cantidad_real = min(cantidad, recurso.cantidad)
            recurso.cantidad = max(0, recurso.cantidad - cantidad_real)
            self.inventario.append((recurso.tipo, cantidad_real))
            return (recurso.tipo, cantidad_real)
        return None

    def duplicar_recoleccion(self, recurso: Recurso):
        self.efectos["recolectando_doble"] = 3

    def mover_hacia_recurso(self, escenario):
        self.mover_aleatorio(escenario)

    def actuar(self, escenario):
        if not self.con_vida:
            return
        x, y = self.posicion_x, self.posicion_y
        celda = escenario.tablero[x][y]
        for entidad in celda.entidades:
            if isinstance(entidad, Recurso) and entidad.cantidad > 0:
                self.recolectar(entidad)
                break
        self.mover_hacia_recurso(escenario)
        self.avanzar_turno()


class Cientifico(Civil):
    def __init__(self, vida: int = 100, ataque: int = 5, defensa: float = None, velocidad: float = 4.0,
                 categoria: str = "Científico", habilidad: str = "Reducción", estado: bool = False,
                 energia: int = 100, posicion_x: int = 0, posicion_y: int = 0, con_vida: bool = True):
        if defensa is None:
            defensa = vida * 0.1
        super().__init__(vida, ataque, defensa, velocidad, categoria, habilidad, estado, energia, posicion_x,
                         posicion_y, con_vida)
        self.inventario = ["Kit Cientifico"]

    def reducir_tiempo_espera(self, civiles: list):
        for civil in civiles:
            if isinstance(civil, Civil) and civil.con_vida and civil.estado and civil.turnos_infeccion is not None:
                civil.turnos_infeccion += 2

    def mover_hacia_infectados(self, escenario):
        self.mover_aleatorio(escenario)

    def actuar(self, escenario):
        if not self.con_vida:
            return
        x, y = self.posicion_x, self.posicion_y
        celda = escenario.tablero[x][y]
        civiles = [e for e in celda.entidades if isinstance(e, Civil) and e.estado and e.con_vida]
        if civiles:
            self.reducir_tiempo_espera(civiles)
        self.mover_hacia_infectados(escenario)
        self.avanzar_turno()


class Medico(Civil):
    def __init__(self, vida: int = 100, ataque: int = 5, defensa: float = None, velocidad: float = 3.0,
                 categoria: str = "Médico", habilidad: str = "Curación", estado: bool = False,
                 energia: int = 150, posicion_x: int = 0, posicion_y: int = 0, con_vida: bool = True):
        if defensa is None:
            defensa = vida * 0.1
        super().__init__(vida, ataque, defensa, velocidad, categoria, habilidad, estado, energia, posicion_x,
                         posicion_y, con_vida)
        self.inventario = ["Vendas"]

    def curar(self, civil: Civil):
        if civil.estado and civil.con_vida:
            civil.estado = False
            civil.turnos_infeccion = None
            return civil
        return None

    def curar_en_celda(self, escenario):
        x = self.posicion_x
        y = self.posicion_y
        celda = escenario.tablero[x][y]

        for entidad in list(celda.entidades):
            if isinstance(entidad, Civil) and entidad.estado and entidad.con_vida:
                return self.curar(entidad)
        return None

    def mover_hacia_infectado(self, escenario):
        self.mover_aleatorio(escenario)

    def actuar(self, escenario):
        if not self.con_vida:
            return
        self.curar_en_celda(escenario)
        self.mover_hacia_infectado(escenario)
        self.avanzar_turno()


# ------------------------- ZOMBIES -------------------------
class Zombie(Personaje):
    def __init__(self, vida: int, ataque: int, defensa: float, velocidad: float, categoria: str, habilidad: str,
                 estado: bool, color: str, posicion_x: int, posicion_y: int, con_vida: bool = True):
        super().__init__(vida, ataque, defensa, velocidad, categoria, habilidad, estado, posicion_x, posicion_y,
                         con_vida)
        self.color = color

    def mover_aleatorio(self, escenario):
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        nuevo_x = self.posicion_x + dx
        nuevo_y = self.posicion_y + dy

        if 0 <= nuevo_x < escenario.ancho and 0 <= nuevo_y < escenario.alto:
            try:
                escenario.tablero[self.posicion_x][self.posicion_y].entidades.remove(self)
            except ValueError:
                pass
            self.posicion_x = nuevo_x
            self.posicion_y = nuevo_y
            escenario.tablero[nuevo_x][nuevo_y].entidades.append(self)


class Verde(Zombie):
    def __init__(self, posicion_x: int, posicion_y: int):
        super().__init__(vida=100, ataque=40, defensa=100 * 0.2, velocidad=3.5, categoria="Normal",
                         habilidad="Escupir", estado=True, color="Verde", posicion_x=posicion_x,
                         posicion_y=posicion_y, con_vida=True)

    def escupir(self, civil: Civil):
        if civil.con_vida and not civil.estado:
            civil.infectar()
            return civil
        return None


class Morado(Zombie):
    def __init__(self, posicion_x: int, posicion_y: int):
        super().__init__(vida=150, ataque=30, defensa=150 * 0.5, velocidad=2.0, categoria="Tanque",
                         habilidad="Aplastar", estado=True, color="Morado", posicion_x=posicion_x,
                         posicion_y=posicion_y, con_vida=True)

    def aplastar(self, civil: Civil):
        if civil.con_vida:
            civil.morir()
            return civil
        return None


class Amarillo(Zombie):
    def __init__(self, posicion_x: int, posicion_y: int):
        super().__init__(vida=80, ataque=50, defensa=80 * 0.1, velocidad=5.5, categoria="Veloz",
                         habilidad="Doble ataque", estado=True, color="Amarillo", posicion_x=posicion_x,
                         posicion_y=posicion_y, con_vida=True)

    def doble_atacar(self, escenario):
        x = self.posicion_x
        y = self.posicion_y
        infectados = []
        for entidad in list(escenario.tablero[x][y].entidades):
            if isinstance(entidad, Civil) and entidad.con_vida and not entidad.estado:
                entidad.infectar()
                infectados.append(entidad)
                if len(infectados) == 2:
                    break
        return infectados


# ------------------------- JUGADOR -------------------------
class Jugador(Civil):
    def __init__(self, vida: int = 100, ataque: int = 25, defensa: float = None, velocidad: float = 4.0,
                 categoria: str = "Jugador", habilidad: str = "Interactuar", estado: bool = False,
                 energia: int = 100, posicion_x: int = 0, posicion_y: int = 0, con_vida: bool = True):
        if defensa is None:
            defensa = vida * 0.3
        super().__init__(vida, ataque, defensa, velocidad, categoria, habilidad, estado, energia, posicion_x,
                         posicion_y, con_vida)
        self.inventario = ["Botiquín", "Mapa"]
        self.efectos["controlado_por_jugador"] = True

    def mover(self, direccion: str, escenario):
        dx = 0
        dy = 0
        if direccion == "W":
            dy = -1
        elif direccion == "S":
            dy = 1
        elif direccion == "A":
            dx = -1
        elif direccion == "D":
            dx = 1

        nuevo_x = self.posicion_x + dx
        nuevo_y = self.posicion_y + dy

        if 0 <= nuevo_x < escenario.ancho and 0 <= nuevo_y < escenario.alto:
            try:
                escenario.tablero[self.posicion_x][self.posicion_y].entidades.remove(self)
            except ValueError:
                pass
            self.posicion_x = nuevo_x
            self.posicion_y = nuevo_y
            escenario.tablero[nuevo_x][nuevo_y].entidades.append(self)

    def atacar_zombie(self, zombie: Zombie):
        if zombie.con_vida:
            daño = max(0, int(self.ataque - zombie.defensa))
            zombie.vida -= daño
            if zombie.vida <= 0:
                zombie.con_vida = False

    def interactuar(self, escenario):
        celda = escenario.tablero[self.posicion_x][self.posicion_y]
        acciones = []

        for entidad in list(celda.entidades):
            if isinstance(entidad, Zombie) and entidad.con_vida:
                self.atacar_zombie(entidad)
                acciones.append(f"Atacaste a un zombi {entidad.color}.")

        for entidad in list(celda.entidades):
            if isinstance(entidad, Civil) and entidad.estado and entidad.con_vida:
                self.curar(entidad)
                acciones.append("Curaste a un civil infectado.")

        for entidad in list(celda.entidades):
            if isinstance(entidad, Recurso) and entidad.cantidad > 0:
                resultado = self.recolectar(entidad)
                if resultado:
                    acciones.append(resultado)
                    if entidad.cantidad <= 0:
                        try:
                            celda.entidades.remove(entidad)
                        except ValueError:
                            pass
                break

        return ", ".join(acciones) if acciones else "Nada que hacer aquí."

    def recolectar(self, recurso):
        if self.energia <= 0:
            return "Estás demasiado cansado para recolectar"

        self.inventario.append((recurso.tipo, 1))
        self.energia -= 1
        return f"Recolectaste {recurso.tipo}"

    def curar(self, civil: Civil):
        if civil.estado and civil.con_vida:
            civil.estado = False
            civil.turnos_infeccion = None


# ------------------------- ESCENARIO -------------------------
class Celda:
    def __init__(self, tipo: str, posicion_x: int, posicion_y: int):
        self.tipo = tipo
        self.posicion_x = posicion_x
        self.posicion_y = posicion_y
        self.entidades = []


class Escenario:
    def __init__(self, ancho: int, alto: int):
        self.ancho = ancho
        self.alto = alto
        self.tablero = [[Celda("campo", x, y) for y in range(alto)] for x in range(ancho)]
        self.recursos = []
        self.personajes = []

    def agregar_personaje(self, personaje):
        x = personaje.posicion_x
        y = personaje.posicion_y
        if 0 <= x < self.ancho and 0 <= y < self.alto:
            self.tablero[x][y].entidades.append(personaje)
            self.personajes.append(personaje)
        else:
            print(f"Posición fuera del tablero: ({x}, {y})")

    def definir_ciudad(self, inicio_x: int, inicio_y: int, ancho: int, alto: int):
        for x in range(inicio_x, min(self.ancho, inicio_x + ancho)):
            for y in range(inicio_y, min(self.alto, inicio_y + alto)):
                self.tablero[x][y].tipo = "ciudad"

    def definir_campo(self, inicio_x: int, inicio_y: int, ancho: int, alto: int):
        for x in range(inicio_x, min(self.ancho, inicio_x + ancho)):
            for y in range(inicio_y, min(self.alto, inicio_y + alto)):
                self.tablero[x][y].tipo = "campo"

    def crear_zombie_aleatorio(self, x: int, y: int):
        tipo = random.choice([Verde, Morado, Amarillo])
        return tipo(x, y)

    def definir_zona_zombie(self, inicio_x: int, inicio_y: int, ancho: int, alto: int):
        for x in range(inicio_x, min(self.ancho, inicio_x + ancho)):
            for y in range(inicio_y, min(self.alto, inicio_y + alto)):
                self.tablero[x][y].tipo = "zona_zombie"
                for _ in range(4):
                    zombi = self.crear_zombie_aleatorio(x, y)
                    self.tablero[x][y].entidades.append(zombi)
                    self.personajes.append(zombi)

    def definir_lago(self, inicio_x: int, inicio_y: int, ancho: int, alto: int):
        for x in range(inicio_x, min(self.ancho, inicio_x + ancho)):
            for y in range(inicio_y, min(self.alto, inicio_y + alto)):
                self.tablero[x][y].tipo = "lago"
                recurso = Recurso("agua", cantidad=50, posicion_x=x, posicion_y=y)
                self.tablero[x][y].entidades.append(recurso)
                self.recursos.append(recurso)

    def definir_rio(self, inicio_x: int, inicio_y: int, ancho: int, alto: int):
        for x in range(inicio_x, min(self.ancho, inicio_x + ancho)):
            for y in range(inicio_y, min(self.alto, inicio_y + alto)):
                self.tablero[x][y].tipo = "rio"
                recurso = Recurso("agua", cantidad=30, posicion_x=x, posicion_y=y)
                self.tablero[x][y].entidades.append(recurso)
                self.recursos.append(recurso)

    def definir_bosque(self, inicio_x: int, inicio_y: int, ancho: int, alto: int):
        for x in range(inicio_x, min(self.ancho, inicio_x + ancho)):
            for y in range(inicio_y, min(self.alto, inicio_y + alto)):
                self.tablero[x][y].tipo = "bosque"
                recurso = Recurso("madera", cantidad=40, posicion_x=x, posicion_y=y)
                self.tablero[x][y].entidades.append(recurso)
                self.recursos.append(recurso)

    def definir_mina(self, inicio_x: int, inicio_y: int, ancho: int, alto: int):
        for x in range(inicio_x, min(self.ancho, inicio_x + ancho)):
            for y in range(inicio_y, min(self.alto, inicio_y + alto)):
                self.tablero[x][y].tipo = "mina"
                recurso = Recurso("mineral", cantidad=30, posicion_x=x, posicion_y=y)
                self.tablero[x][y].entidades.append(recurso)
                self.recursos.append(recurso)

    def imprimir_tablero(self):
        simbolos = {"ciudad": "C", "campo": "F", "zona_zombie": "Z", "lago": "L", "rio": "R", "bosque": "B", "mina": "M"}

        for y in range(self.alto):
            fila = ""
            for x in range(self.ancho):
                tipo = self.tablero[x][y].tipo
                fila += simbolos.get(tipo, "?") + " "
            print(fila)

    def poblar_ciudad(self, cantidad_normales: int, cantidad_atacantes: int, cantidad_defensores: int,
                      cantidad_productores: int, cantidad_cientificos: int, cantidad_medicos: int,
                      inicio_x: int, inicio_y: int, ancho: int, alto: int):
        for _ in range(cantidad_normales):
            x = random.randint(inicio_x, min(inicio_x + ancho - 1, self.ancho - 1))
            y = random.randint(inicio_y, min(inicio_y + alto - 1, self.alto - 1))
            civil = Civil_Normal(posicion_x=x, posicion_y=y)
            self.agregar_personaje(civil)

        for _ in range(cantidad_atacantes):
            x = random.randint(inicio_x, min(inicio_x + ancho - 1, self.ancho - 1))
            y = random.randint(inicio_y, min(inicio_y + alto - 1, self.alto - 1))
            atacante = Atacante(posicion_x=x, posicion_y=y)
            self.agregar_personaje(atacante)

        for _ in range(cantidad_defensores):
            x = random.randint(inicio_x, min(inicio_x + ancho - 1, self.ancho - 1))
            y = random.randint(inicio_y, min(inicio_y + alto - 1, self.alto - 1))
            defensor = Defensor(posicion_x=x, posicion_y=y)
            self.agregar_personaje(defensor)

        for _ in range(cantidad_productores):
            x = random.randint(inicio_x, min(inicio_x + ancho - 1, self.ancho - 1))
            y = random.randint(inicio_y, min(inicio_y + alto - 1, self.alto - 1))
            productor = Productor(posicion_x=x, posicion_y=y)
            self.agregar_personaje(productor)

        for _ in range(cantidad_cientificos):
            x = random.randint(inicio_x, min(inicio_x + ancho - 1, self.ancho - 1))
            y = random.randint(inicio_y, min(inicio_y + alto - 1, self.alto - 1))
            cientifico = Cientifico(posicion_x=x, posicion_y=y)
            self.agregar_personaje(cientifico)

        for _ in range(cantidad_medicos):
            x = random.randint(inicio_x, min(inicio_x + ancho - 1, self.ancho - 1))
            y = random.randint(inicio_y, min(inicio_y + alto - 1, self.alto - 1))
            medico = Medico(posicion_x=x, posicion_y=y)
            self.agregar_personaje(medico)

    def poblar_zona_zombie(self, cantidad_zombies: int, inicio_x: int, inicio_y: int, ancho: int, alto: int):
        for _ in range(cantidad_zombies):
            x = random.randint(inicio_x, min(inicio_x + ancho - 1, self.ancho - 1))
            y = random.randint(inicio_y, min(inicio_y + alto - 1, self.alto - 1))
            zombi = self.crear_zombie_aleatorio(x, y)
            self.agregar_personaje(zombi)

    def simular_turno(self):
        """Simula un turno y devuelve lista de eventos (categoria, mensaje)."""
        eventos = []

        # 1. Avance de estados internos
        for personaje in list(self.personajes):
            if isinstance(personaje, Civil):
                personaje.avanzar_turno()
                if not personaje.con_vida:
                    eventos.append(("General", f"{personaje.__class__.__name__} murió por infección en ({personaje.posicion_x},{personaje.posicion_y})."))
                    try:
                        self.tablero[personaje.posicion_x][personaje.posicion_y].entidades.remove(personaje)
                    except Exception:
                        pass
                    if personaje in self.personajes:
                        self.personajes.remove(personaje)

        # 2. Movimiento y acciones
        for personaje in list(self.personajes):
            if not personaje.con_vida:
                continue

            # NO MOVER AL JUGADOR (solo controlado por el usuario)
            if isinstance(personaje, Jugador):
                continue

            # mover por tipo
            try:
                personaje.mover_aleatorio(self)
            except Exception:
                pass

            if isinstance(personaje, Medico):
                curado = personaje.curar_en_celda(self)
                if curado:
                    eventos.append(("Medicos", f"Médico cura a {curado.__class__.__name__} en ({personaje.posicion_x},{personaje.posicion_y})."))

            elif isinstance(personaje, Cientifico):
                x = personaje.posicion_x
                y = personaje.posicion_y
                cel = self.tablero[x][y]
                infectados = [e for e in cel.entidades if isinstance(e, Civil) and e.estado and e.con_vida]
                if infectados:
                    personaje.reducir_tiempo_espera(infectados)
                    eventos.append(("Cientificos", f"Científico ayuda a {len(infectados)} infectado(s) en ({x},{y})."))

            elif isinstance(personaje, Productor):
                x = personaje.posicion_x
                y = personaje.posicion_y
                cel = self.tablero[x][y]
                for ent in list(cel.entidades):
                    if isinstance(ent, Recurso) and ent.cantidad > 0:
                        res = personaje.recolectar(ent)
                        if res:
                            eventos.append(("Productores", f"Productor en ({x},{y}) recolecta {res[1]}x {res[0]}."))
                        break

            elif isinstance(personaje, Atacante):
                resultado = personaje.atacar(self)
                if resultado:
                    tipo, daño, killed, pos = resultado
                    eventos.append(("Atacantes", f"Atacante en ({pos[0]},{pos[1]}) ataca {tipo} (-{daño} vida)."))
                    if killed:
                        eventos.append(("Atacantes", f"Atacante mata a {tipo} en ({pos[0]},{pos[1]})."))

            elif isinstance(personaje, Defensor):
                x = personaje.posicion_x
                y = personaje.posicion_y
                cel = self.tablero[x][y]
                for entidad in cel.entidades:
                    if isinstance(entidad, Civil) and entidad.con_vida and entidad is not personaje:
                        protegido = personaje.proteger(entidad)
                        if protegido:
                            eventos.append(("Defensores", f"Defensor protege a {entidad.__class__.__name__} en ({x},{y})."))
                        break

            elif isinstance(personaje, Verde):
                x = personaje.posicion_x
                y = personaje.posicion_y
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        nx = x + dx
                        ny = y + dy
                        if 0 <= nx < self.ancho and 0 <= ny < self.alto:
                            celda = self.tablero[nx][ny]
                            for entidad in list(celda.entidades):
                                if isinstance(entidad, Civil) and entidad.con_vida and not entidad.estado:
                                    infectado = personaje.escupir(entidad)
                                    if infectado:
                                        eventos.append(("Zombie_Verde", f"Zombi Verde infecta a {infectado.__class__.__name__} en ({nx},{ny})."))
                                    break

            elif isinstance(personaje, Morado):
                x = personaje.posicion_x
                y = personaje.posicion_y
                cel = self.tablero[x][y]
                for entidad in list(cel.entidades):
                    if isinstance(entidad, Civil) and entidad.con_vida:
                        muerto = personaje.aplastar(entidad)
                        if muerto:
                            eventos.append(("Zombie_Morado", f"Zombi Morado aplasta a {muerto.__class__.__name__} en ({x},{y})."))
                            try:
                                cel.entidades.remove(muerto)
                            except ValueError:
                                pass
                            if muerto in self.personajes:
                                self.personajes.remove(muerto)
                        break

            elif isinstance(personaje, Amarillo):
                infectados = personaje.doble_atacar(self)
                if infectados:
                    x = personaje.posicion_x
                    y = personaje.posicion_y
                    eventos.append(("Zombie_Amarillo", f"Zombi Amarillo infecta {len(infectados)} civil(es) en ({x},{y})."))

        return eventos


# ------------------------- PERSISTENCIA Y CONTROLADOR -------------------------
class Persistencia:
    def __init__(self):
        self.cantidad = 0

    def guarda(self, escenario, jugador, nombre_archivo: str = "partida_guardada.cc"):
        try:
            datos = {
                'escenario': escenario,
                'jugador': jugador
            }
            with open(nombre_archivo, 'wb') as fos:
                pickle.dump(datos, fos)
            return True
        except Exception as e:
            print(f"Error al guardar: {e}")
            return False

    def rescatar(self, nombre_archivo: str = "partida_guardada.cc"):
        try:
            with open(nombre_archivo, 'rb') as fis:
                datos = pickle.load(fis)
                return datos.get('escenario'), datos.get('jugador')
        except Exception as e:
            print(f"Error al rescatar: {e}")
            return None, None


class Controlador:
    def __init__(self):
        self.persistencia = Persistencia()
        self.ultimo_guardado = False

    def guardar_partida(self, escenario, jugador, nombre: str = "partida_guardada.cc"):
        ok = self.persistencia.guarda(escenario, jugador, nombre)
        self.ultimo_guardado = ok
        return ok


# ------------------------- VISTA (Pygame) -------------------------
class Vista:
    def __init__(self, escenario: Escenario, jugador: Jugador, ancho_ventana: int = 800, alto_ventana: int = 600):
        pygame.init()
        self.jugador = jugador
        self.escenario = escenario
        self.ancho_ventana = ancho_ventana
        self.barra_ancho = 300
        self.controlador = Controlador()

        info = pygame.display.Info()
        pantalla_alto = info.current_h
        margen = 50
        celda_alto = max(8, min(24, (pantalla_alto - margen) // max(1, self.escenario.alto)))
        self.alto_ventana = celda_alto * self.escenario.alto

        # limitar ancho para que quepa la barra lateral
        self.ventana_ancho_total = self.ancho_ventana
        self.ventana = pygame.display.set_mode((self.ventana_ancho_total, self.alto_ventana))
        pygame.display.set_caption("GeoZ4 - Simulación de Supervivencia Zombie")
        self.reloj = pygame.time.Clock()

        self.mensajes = []
        self.sidebar_scroll = 0
        self.sidebar_line_h = 22
        self.sidebar_scroll_speed = 3

        self.celda_ancho = (self.ventana_ancho_total - self.barra_ancho) // max(1, self.escenario.ancho)
        self.celda_alto = self.alto_ventana // max(1, self.escenario.alto)

        self.correr_simulacion()

    def ejecutar_turno(self):
        eventos = self.escenario.simular_turno()
        for categoria, mensaje in eventos:
            self.mensajes.append(mensaje)
        while len(self.mensajes) > 50:
            self.mensajes.pop(0)

    def correr_simulacion(self):
        corriendo = True
        contador_turnos = 0

        while corriendo:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    corriendo = False
                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_w:
                        self.jugador.mover("W", self.escenario)
                    elif evento.key == pygame.K_s:
                        self.jugador.mover("S", self.escenario)
                    elif evento.key == pygame.K_a:
                        self.jugador.mover("A", self.escenario)
                    elif evento.key == pygame.K_d:
                        self.jugador.mover("D", self.escenario)
                    elif evento.key == pygame.K_e:
                        resultado = self.jugador.interactuar(self.escenario)
                        if resultado:
                            self.mensajes.append(resultado)
                    elif evento.key == pygame.K_g:
                        guardado = self.controlador.guardar_partida(self.escenario, self.jugador)
                        if guardado:
                            self.mensajes.append("🎉 Partida guardada correctamente.")
                        else:
                            self.mensajes.append("❌ Error al guardar la partida.")

                elif evento.type == pygame.MOUSEWHEEL:
                    delta_px = -evento.y * self.sidebar_line_h * self.sidebar_scroll_speed
                    self.sidebar_scroll += delta_px

            # actualizar pantalla
            self.ventana.fill((0, 0, 0))
            self.dibujar_escenario()
            self.dibujar_barra_lateral()

            pygame.display.flip()

            contador_turnos += 1
            if contador_turnos >= 12:  # cada N frames ejecuta turno
                self.ejecutar_turno()
                contador_turnos = 0

            if not self.jugador.con_vida:
                if not any("ha muerto" in m.lower() for m in self.mensajes):
                    self.mensajes.append("El jugador ha muerto. Fin de la simulación.")
                pygame.time.delay(2000)
                corriendo = False
                break

            self.reloj.tick(30)

        pygame.quit()

    def dibujar_escenario(self):
        # recalcular tamaños por si cambió la ventana
        self.celda_ancho = (self.ventana_ancho_total - self.barra_ancho) // max(1, self.escenario.ancho)
        self.celda_alto = self.alto_ventana // max(1, self.escenario.alto)

        for x in range(self.escenario.ancho):
            for y in range(self.escenario.alto):
                celda = self.escenario.tablero[x][y]
                color_celda = (34, 139, 34)

                if celda.tipo == "ciudad":
                    color_celda = (169, 169, 169)
                elif celda.tipo == "zona_zombie":
                    color_celda = (80, 0, 0)
                elif celda.tipo == "campo":
                    color_celda = (34, 139, 34)
                elif celda.tipo == "lago":
                    color_celda = (0, 191, 255)
                elif celda.tipo == "rio":
                    color_celda = (30, 144, 255)
                elif celda.tipo == "bosque":
                    color_celda = (0, 100, 0)
                elif celda.tipo == "mina":
                    color_celda = (139, 69, 19)

                rect_x = x * self.celda_ancho
                rect_y = y * self.celda_alto
                pygame.draw.rect(self.ventana, color_celda, (rect_x, rect_y, self.celda_ancho, self.celda_alto))

                for entidad in celda.entidades:
                    if entidad is self.jugador:
                        color_entidad = (0, 0, 0)
                    elif isinstance(entidad, Civil_Normal):
                        color_entidad = (0, 0, 255)
                    elif isinstance(entidad, Atacante):
                        color_entidad = (0, 255, 255)
                    elif isinstance(entidad, Defensor):
                        color_entidad = (255, 165, 0)
                    elif isinstance(entidad, Productor):
                        color_entidad = (255, 192, 203)
                    elif isinstance(entidad, Cientifico):
                        color_entidad = (75, 0, 150)
                    elif isinstance(entidad, Medico):
                        color_entidad = (0, 255, 0)
                    elif isinstance(entidad, Verde):
                        color_entidad = (34, 119, 34)
                    elif isinstance(entidad, Morado):
                        color_entidad = (128, 0, 128)
                    elif isinstance(entidad, Amarillo):
                        color_entidad = (255, 255, 0)
                    elif isinstance(entidad, Recurso):
                        color_entidad = (200, 200, 200)
                    else:
                        continue

                    cx = rect_x + self.celda_ancho // 2
                    cy = rect_y + self.celda_alto // 2
                    radius = max(2, min(self.celda_ancho, self.celda_alto) // 4)
                    pygame.draw.circle(self.ventana, color_entidad, (cx, cy), radius)

    def dibujar_barra_lateral(self):
        fuente = pygame.font.SysFont(None, 20)
        x_base = self.ventana_ancho_total - self.barra_ancho + 10

        pygame.draw.rect(self.ventana, (30, 30, 30), (self.ventana_ancho_total - self.barra_ancho, 0, self.barra_ancho, self.alto_ventana))

        lines = []
        lines.append("🧍 JUGADOR")
        lines.append(" ----------CONTROLES---------- ")
        lines.append("W = Arriba, A = Izquierda")
        lines.append("S = Abajo, D = Derecha")
        lines.append("E: Interactuar, G: Guardar partida")
        lines.append(" ---------------------------- ")
        lines.append(f"Vida: {self.jugador.vida}")
        lines.append(f"Energía: {self.jugador.energia}")
        lines.append(f"Infectado: {'Sí' if self.jugador.estado else 'No'}")
        lines.append(f"Posición: ({self.jugador.posicion_x}, {self.jugador.posicion_y})")
        lines.append(f"Guardado: {'Sí' if self.controlador.ultimo_guardado else 'No'}")
        lines.append("Inventario:")
        for item in self.jugador.inventario:
            lines.append(f" - {item}")
        lines.append("")
        lines.append("Últimas acciones:")
        for mensaje in reversed(self.mensajes[-20:]):
            lines.append(f"• {mensaje}")

        total_lines = len(lines)
        total_height = total_lines * self.sidebar_line_h
        visible_height = self.alto_ventana
        max_scroll_px = max(0, total_height - visible_height)

        if self.sidebar_scroll < 0:
            self.sidebar_scroll = 0
        if self.sidebar_scroll > max_scroll_px:
            self.sidebar_scroll = max_scroll_px

        start_line = int(self.sidebar_scroll // self.sidebar_line_h)
        y_offset_px = -(self.sidebar_scroll % self.sidebar_line_h)

        y = y_offset_px + 10
        max_visible_lines = visible_height // self.sidebar_line_h + 2
        end_line = min(total_lines, start_line + max_visible_lines)

        for idx in range(start_line, end_line):
            text = lines[idx]
            color = (200, 200, 100) if text.startswith("•") else (255, 255, 255)
            render = fuente.render(text, True, color)
            self.ventana.blit(render, (x_base, y))
            y += self.sidebar_line_h

        if total_height > visible_height:
            bar_w = 8
            bar_x = self.ventana_ancho_total - 14
            bar_y = 4
            bar_h = visible_height - 8
            pygame.draw.rect(self.ventana, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))

            handle_h = max(20, int(bar_h * (visible_height / total_height)))
            if max_scroll_px > 0:
                handle_y = bar_y + int((bar_h - handle_h) * (self.sidebar_scroll / max_scroll_px))
            else:
                handle_y = bar_y
            pygame.draw.rect(self.ventana, (160, 160, 160), (bar_x, handle_y, bar_w, handle_h))


# ------------------------- MENU INICIAL Y CONFIGURACIÓN -------------------------
def crear_escenario_predeterminado():
    escenario = Escenario(50, 50)

    escenario.definir_ciudad(17, 17, 16, 16)

    escenario.definir_zona_zombie(0, 0, 5, 5)
    escenario.definir_zona_zombie(45, 0, 5, 5)
    escenario.definir_zona_zombie(0, 45, 5, 5)
    escenario.definir_zona_zombie(45, 45, 5, 5)

    escenario.definir_lago(20, 40, 5, 5)
    escenario.definir_lago(5, 5, 6, 6)
    escenario.definir_lago(44, 15, 4, 4)

    escenario.definir_rio(7, 14, 30, 2)
    escenario.definir_rio(33, 33, 2, 10)
    escenario.definir_bosque(5, 20, 8, 8)
    escenario.definir_bosque(35, 5, 10, 10)

    escenario.poblar_ciudad(
        cantidad_normales=10,
        cantidad_atacantes=5,
        cantidad_defensores=3,
        cantidad_productores=4,
        cantidad_cientificos=2,
        cantidad_medicos=3,
        inicio_x=17, inicio_y=17, ancho=16, alto=16
    )

    return escenario


def menu_inicial():
    pygame.init()
    ancho = 600
    alto = 400
    pantalla = pygame.display.set_mode((ancho, alto))
    pygame.display.set_caption("GeoZ4 - Menú")
    fuente = pygame.font.SysFont(None, 36)
    clock = pygame.time.Clock()

    seleccion = None
    while seleccion is None:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_n:  # Nueva partida
                    seleccion = 'n'
                elif evento.key == pygame.K_l:  # Cargar partida
                    seleccion = 'l'
                elif evento.key == pygame.K_q:  # Salir
                    pygame.quit()
                    sys.exit()

        pantalla.fill((20, 20, 20))
        pantalla.blit(fuente.render("GeoZ4 - Simulación Zombie", True, (255, 255, 255)), (50, 40))
        pantalla.blit(fuente.render("N - Nueva partida", True, (200, 200, 200)), (50, 120))
        pantalla.blit(fuente.render("L - Cargar partida", True, (200, 200, 200)), (50, 170))
        pantalla.blit(fuente.render("Q - Salir", True, (200, 200, 200)), (50, 220))

        pantalla.blit(fuente.render("Controles: W A S D, E interactuar, G guardar", True, (160, 160, 160)), (50, 300))

        pygame.display.flip()
        clock.tick(30)

    pygame.display.quit()
    return seleccion


# ------------------------- PUNTO DE ENTRADA -------------------------
if __name__ == '__main__':
    opcion = menu_inicial()

    controlador_global = Controlador()
    escenario = None
    jugador = None

    if opcion == 'l':
        esc, jug = controlador_global.persistencia.rescatar()
        if esc is not None and jug is not None:
            escenario = esc
            jugador = jug
            print("Partida cargada.")
        else:
            print("No se encontró partida válida. Creando nueva partida.")
            escenario = crear_escenario_predeterminado()
    else:
        escenario = crear_escenario_predeterminado()

    # crear jugador (si la carga no lo incluyó)
    if jugador is None:
        jugador = Jugador(posicion_x=24, posicion_y=24)
        escenario.agregar_personaje(jugador)
    else:
        # si se cargó un jugador, asegurarse que esté en el tablero
        if jugador not in escenario.personajes:
            escenario.agregar_personaje(jugador)

    vista = Vista(escenario, jugador, ancho_ventana=1200, alto_ventana=800)