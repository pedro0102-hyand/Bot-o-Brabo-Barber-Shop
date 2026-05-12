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

    # Opções de serviços disponíveis
    SERVICOS = [
        ("corte", "Corte de Cabelo"),
        ("barba", "Barba"),
        ("corte_barba", "Corte + Barba"),
        ("hidratacao", "Hidratação Capilar"),
        ("sobrancelha", "Sobrancelha"),
    ]

    # Opções de status para o agendamento
    STATUS = [
        ("pendente", "Pendente"),
        ("confirmado", "Confirmado"),
        ("cancelado", "Cancelado"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="agendamentos") # Relacionamento com Cliente
    servico = models.CharField(max_length=20, choices=SERVICOS) # Tipo de serviço escolhido
    data = models.DateField() # Data do agendamento
    horario = models.TimeField() # Horário do agendamento
    status = models.CharField(max_length=20, choices=STATUS, default="confirmado") # Status do agendamento
    criado_em = models.DateTimeField(auto_now_add=True) # Data e hora de criação do agendamento

    class Meta:
        unique_together = ("data", "horario")

    def __str__(self):
        return f"{self.cliente.nome} - {self.servico} - {self.data} {self.horario}"
