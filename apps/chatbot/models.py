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
