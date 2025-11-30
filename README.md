import pickle

class Escenario:
    def __init__(self):
        self.cosas_varias = 2
    
    def mostrar(self):
        print(f"soy un escenario con {self.cosas_varias} cosas ")  # Corregido: agregado self.
              
class Persistencia:
    def __init__(self):
        self.cantidad = 0
    
    def guarda(self, escenario):
        try:
            with open("miarchivo.cc", 'wb') as fos:
                oos = pickle.Pickler(fos)
                oos.dump(escenario)
        except Exception as e:
            raise Exception(f"Error al guardar: {e}")
    
    def rescatar(self):
        try:
            with open("miarchivo.cc", 'rb') as fis:
                ois = pickle.Unpickler(fis)
                e_rescatado = ois.load()
                e_rescatado.mostrar()  # Asume que Escenario tiene método mostrar()
                return e_rescatado
        except Exception as e:
            raise Exception(f"Error al rescatar: {e}")

e = Escenario()
p = Persistencia()
p.guarda(e)
e2 = p.rescatar()
e2.mostrar()
