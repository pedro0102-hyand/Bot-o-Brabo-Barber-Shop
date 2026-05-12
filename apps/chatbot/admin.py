from django.contrib import admin
from .models import Cliente, Conversa, Agendamento


@admin.register(Cliente)

class ClienteAdmin(admin.ModelAdmin):

    list_display = ("nome", "telegram_id", "criado_em")
    search_fields = ("nome", "telegram_id")


@admin.register(Conversa)

class ConversaAdmin(admin.ModelAdmin):

    list_display = ("cliente", "intencao", "mensagem", "criado_em")
    list_filter = ("intencao",)
    search_fields = ("mensagem", "resposta")
    readonly_fields = ("cliente", "mensagem", "resposta", "intencao", "criado_em")

@admin.register(Agendamento)

class AgendamentoAdmin(admin.ModelAdmin):

    list_display = ("cliente", "servico", "data", "horario", "status", "criado_em")
    list_filter = ("servico", "status", "data")
    search_fields = ("cliente__nome",)
    