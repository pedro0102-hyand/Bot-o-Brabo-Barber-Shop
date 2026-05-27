from django.contrib import admin
from .models import Cliente, Conversa, Agendamento, EstadoAgendamento


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
    # Sem list_per_page, Django carrega todos os registros — com volume alto
    # de mensagens o admin trava. 25 por página é o padrão do Django;
    # reduzimos para 20 por linha ser mais verbosa (mensagem + resposta completas).
    list_per_page = 20
    # Ordena do mais recente para o mais antigo por padrão.
    ordering = ("-criado_em",)
    # Permite filtrar por período sem precisar da busca manual por data.
    date_hierarchy = "criado_em"


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "servico", "data", "horario", "status", "criado_em")
    list_filter = ("servico", "status", "data")
    search_fields = ("cliente__nome",)
    list_per_page = 25
    ordering = ("-data", "horario")
    date_hierarchy = "data"


@admin.register(EstadoAgendamento)
class EstadoAgendamentoAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "atualizado_em")
    readonly_fields = ("telegram_id", "dados", "atualizado_em")