from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('find_match/', views.find_match, name='find_match'),
    path('chat/', views.chat, name='chat'),
    path('chat/<str:room_id>/', views.chat_view, name='chat_view'),
    path('leave/', views.leave_chat, name='leave_chat'),
    path('profile/', views.profile, name='profile'),  
    path('edit-profile-save', views.editar_perfil, name="editar_perfil"),
    path('edit-profile', views.editar_perfil_view, name='edit_profile'),

    path('register/', views.register, name='register'),
    path('confirm-token/', views.confirm_token, name='confirm_token'),
    path('login/', views.login_view, name='login'),

    path('adicionar_amigo/<int:usuario_id>/', views.adicionar_amigo, name='adicionar_amigo'),
    path('usuario/<int:usuario_id>/', views.perfil_usuario, name='perfil_usuario'),
    path('usuario/<int:usuario_id>/recado/', views.enviar_recado, name='enviar_recado'),

    path('conversation/<uuid:conv_id>/', views.conversation_view, name='conversation'),
    path('conversation/<uuid:conv_id>/send/', views.send_conversation_message, name='send_conversation_message'),
    path(
      'conversation/<uuid:conv_id>/messages/',
      views.conversation_messages_json,
      name='conversation_messages_json'
    ),
    path('recado/mover/<int:recado_id>/', views.mover_recado, name='mover_recado'),
    path('excluir_recado/<int:recado_id>/', views.excluir_recado, name='excluir_recado'),
    path('excluir_recado_usuario/<int:recado_id>/', views.excluir_recado_usuario, name='excluir_recado_usuario'),

    path('clubes/', views.clubes_lista, name='clubes_lista'),
    path('clubes/criar/', views.clubes_criar, name='clubes_criar'),
    path('clubes/<int:pk>/', views.clubes_detalhe, name='clubes_detalhe'),
    path('clubes/<int:pk>/editar/', views.clubes_editar, name='clubes_editar'),
    path('clubes/<int:pk>/entrar/', views.clubes_entrar, name='clubes_entrar'),
    path('clubes/<int:pk>/gerenciar_solicitacoes/', views.gerenciar_solicitacoes, name='gerenciar_solicitacoes'),
    path('clubes/<int:clube_id>/solicitacao/<int:solicitacao_id>/aprovar/', views.clubes_aprovar_solicitacao, name='clubes_aprovar_solicitacao'),
    path('clubes/<int:clube_id>/solicitacao/<int:solicitacao_id>/rejeitar/', views.clubes_rejeitar_solicitacao, name='clubes_rejeitar_solicitacao'),
    path('clubes/<int:pk>/sair/', views.clubes_sair, name='clubes_sair'),

    path('clubes/<int:clube_id>/nova_discussao/', views.clube_nova_discussao, name='clube_nova_discussao'), 
    path('clubes/<int:clube_id>/topico/<int:topico_id>/', views.clube_topico, name='clube_topico'),
 
    path('clubes/<int:clube_id>/criar_sala/', views.criar_sala, name='criar_sala'),

    path('salas/<int:sala_id>/', views.sala_detalhe, name='sala_detalhe'),
    path('salas/<int:sala_id>/enviar/', views.enviar_mensagem, name='enviar_mensagem'),

    path('notificacoes/', views.notificacoes, name='notificacoes'),

    path('clubes/<int:clube_id>/criar_evento/', views.criar_evento, name='criar_evento'),

    path('bloquear/<int:id>/', views.bloquear_usuario, name='bloquear_usuario'),
    path('desbloquear/<int:id>/', views.desbloquear_usuario, name='desbloquear_usuario'),
    
    path('wplace/', views.wplace_view, name='wplace'),
    path('wplace/state/', views.wplace_state, name='wplace_state'),
]
