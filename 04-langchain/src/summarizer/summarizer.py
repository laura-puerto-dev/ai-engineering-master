from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Resume el texto introducido por el usuario. Devuelve exactamente 3 viñetas. Cada viñeta debe ocupar una línea y comenzar exactamente por - . No incluyas ninguna introducción ni texto adicional.",
        ),
        ("human", "{text}"),
    ]
)

model = ChatOllama(model="llama3.1", temperature=0)

parser = StrOutputParser()

chain = prompt | model | parser

texts = {
    "Inteligencia artificial": """La inteligencia artificial está transformando la forma en que las empresas gestionan la atención al cliente. Los sistemas basados en modelos de lenguaje pueden responder preguntas frecuentes, ayudar a localizar información y asistir a los usuarios durante diferentes procesos sin necesidad de intervención humana en cada interacción. Esto permite reducir los tiempos de espera y ofrecer atención durante las veinticuatro horas del día.
Sin embargo, incorporar inteligencia artificial a un servicio de atención al cliente no consiste simplemente en conectar un modelo de lenguaje a una interfaz de chat. Las empresas deben proporcionar al sistema acceso a información actualizada, definir qué acciones puede realizar y establecer mecanismos para evitar respuestas incorrectas. En muchos casos, el modelo necesita consultar bases de datos, documentación interna o servicios externos antes de poder responder de forma fiable.
También es importante decidir qué tareas deben automatizarse y cuáles requieren intervención humana. Una consulta sencilla sobre el estado de un pedido puede resolverse automáticamente, mientras que una reclamación compleja puede necesitar ser transferida a un agente humano. Por este motivo, los sistemas conversacionales modernos suelen combinar modelos de lenguaje con reglas de negocio, herramientas externas y mecanismos de escalado a personas.
Finalmente, estos sistemas deben evaluarse de forma continua. Aspectos como la precisión de las respuestas, la latencia, el coste, la satisfacción del usuario y la frecuencia con la que el sistema necesita ayuda humana permiten determinar si la solución está funcionando correctamente y detectar oportunidades de mejora.
""",
    "Fuentes de energía renovables": """La transición hacia fuentes de energía renovable está cambiando profundamente la forma en que se produce y distribuye la electricidad. Tecnologías como la energía solar y la eólica permiten generar electricidad sin utilizar combustibles fósiles durante su funcionamiento y han experimentado una importante reducción de costes durante los últimos años. Como consecuencia, cada vez representan una proporción mayor de la capacidad eléctrica instalada en numerosos países.
Uno de los principales desafíos de estas tecnologías es que su producción depende de condiciones ambientales que no pueden controlarse. Los paneles solares producen electricidad cuando existe suficiente radiación solar y los aerogeneradores necesitan unas determinadas condiciones de viento. Esto significa que la generación eléctrica puede variar a lo largo del día y no siempre coincide con los momentos en los que los consumidores demandan más energía.
Los sistemas de almacenamiento pueden ayudar a resolver parte de este problema. Las baterías permiten almacenar electricidad cuando existe un exceso de producción y utilizarla posteriormente cuando la generación renovable disminuye o aumenta la demanda. Además del almacenamiento mediante baterías, existen otras tecnologías como el almacenamiento hidroeléctrico por bombeo, el almacenamiento térmico y diferentes soluciones basadas en hidrógeno.
La evolución de las redes eléctricas también será importante para integrar cantidades cada vez mayores de generación renovable. Las redes inteligentes pueden utilizar sensores, sistemas de comunicación y software para conocer mejor el estado de la red y coordinar producción, almacenamiento y consumo. La combinación de generación renovable, almacenamiento y una gestión más flexible de la demanda será una de las piezas fundamentales de los sistemas eléctricos del futuro.
""",
}


def main() -> None:
    for name, text in texts.items():
        chain_input = {"text": text}
        output = chain.invoke(chain_input)

        lines = output.splitlines()
        bullets = [line for line in lines if line.startswith("- ")]

        if len(bullets) != 3:
            raise ValueError(
                f"Se esperaban 3 bullets, pero se recibieron {len(bullets)}"
            )

        word_count = len(text.split())
        print(f"*** {name} ({word_count} palabras) ***")
        print(output)
        print("\n\n")


if __name__ == "__main__":
    main()
