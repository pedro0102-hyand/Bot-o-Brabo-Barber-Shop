from django.db import models


class Cliente(models.Model):

    telegram_id = models.CharField(max_length=50, unique=True)
    nome = models.CharField(max_length=100, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} ({self.telegram_id})"


class Conversa(models.Model):

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="conversas")
    mensagem = models.TextField()
    resposta = models.TextField()
    intencao = models.CharField(max_length=50, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cliente.nome} - {self.criado_em.strftime('%d/%m/%Y %H:%M')}"


class Agendamento(models.Model):

    SERVICOS = [
        ("corte", "Corte de Cabelo"),
        ("barba", "Barba"),
        ("corte_barba", "Corte + Barba"),
        ("hidratacao", "Hidratação Capilar"),
        ("sobrancelha", "Sobrancelha"),
    ]

    STATUS = [
        ("pendente", "Pendente"),
        ("confirmado", "Confirmado"),
        ("cancelado", "Cancelado"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="agendamentos")
    servico = models.CharField(max_length=20, choices=SERVICOS)
    data = models.DateField()
    horario = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS, default="confirmado")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("data", "horario")

    def __str__(self):
        return f"{self.cliente.nome} - {self.servico} - {self.data} {self.horario}"


class EstadoAgendamento(models.Model):

    telegram_id = models.CharField(max_length=50, unique=True)
    dados = models.JSONField(default=dict)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Estado de {self.telegram_id}"