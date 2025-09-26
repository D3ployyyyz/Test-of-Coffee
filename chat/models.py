from django.db import models
from django.utils import timezone

class WaitingUser(models.Model):
    session_id = models.CharField(max_length=100, unique=True)
    joined_at = models.DateTimeField(default=timezone.now)

# models.py
from django.db import models

class ChatRoom(models.Model):
    id = models.CharField(primary_key=True, max_length=16)
    user1 = models.CharField(max_length=100)
    user2 = models.CharField(max_length=100)

from django.db import models
from django.utils import timezone
from datetime import timedelta, date
import uuid

class Clube(models.Model):
    nome = models.CharField(max_length=100)
    imagem = models.URLField()
    idioma = models.CharField(max_length=50, default='Português (Brasil)')
    categoria = models.CharField(max_length=50, default='Cotidiano')
    tipo = models.CharField(
        max_length=20,
        choices=[('Pública', 'Pública'), ('Privada', 'Privada'), ('Fechada', 'Fechada')]
    )
    data = models.DateField(default=date.today)
    dono = models.CharField(max_length=100)
    mods = models.TextField(blank=True)
    descricao = models.TextField()
    membros = models.IntegerField(default=1)

    def __str__(self):
        return self.nome

class Usuario(models.Model):
    nome = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    senha = models.CharField(max_length=128)
    session_key = models.CharField(max_length=100, blank=True, null=True) 

    # Verificação
    token_verificacao = models.CharField(max_length=36, blank=True, null=True)
    token_expiracao = models.DateTimeField(blank=True, null=True)

    # Campos do perfil
    foto = models.TextField(blank=True, null=True)
    emoji = models.CharField(max_length=2, blank=True, null=True)
    descricao = models.TextField(blank=True, null=True)
    localizacao = models.CharField(max_length=100, blank=True, null=True)
    gostos = models.JSONField(blank=True, null=True)
    redes_sociais = models.JSONField(blank=True, null=True)
    playlist = models.URLField(blank=True, null=True)

    # NOVOS CAMPOS
    criado_em = models.DateTimeField(auto_now_add=True)
    ultimo_acesso = models.DateField(blank=True, null=True)
    dias_consecutivos = models.IntegerField(default=0)

    # Relações
    amigos = models.ManyToManyField("self", symmetrical=True, blank=True)
    clubes = models.ManyToManyField(Clube, blank=True)

    def token_valido(self):
        return self.token_expiracao and self.token_expiracao > timezone.now()

    def registrar_acesso(self):
        hoje = timezone.now().date()
        if self.ultimo_acesso:
            if self.ultimo_acesso == hoje:
                return
            elif self.ultimo_acesso == hoje - timedelta(days=1):
                self.dias_consecutivos += 1
            else:
                self.dias_consecutivos = 1
        else:
            self.dias_consecutivos = 1

        self.ultimo_acesso = hoje
        self.save()

    bloqueados = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='bloqueado_por',
        blank=True
    )

    def bloquear(self, outro_usuario):
        self.bloqueados.add(outro_usuario)

    def desbloquear(self, outro_usuario):
        self.bloqueados.remove(outro_usuario)

    def esta_bloqueado(self, outro_usuario):
        return outro_usuario in self.bloqueados.all()

    def __str__(self):
        return self.nome

import uuid
from django.db import models

import uuid
from django.db import models

class Conversation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user1 = models.ForeignKey(
        'Usuario',
        on_delete=models.CASCADE,
        related_name='conversations_started'
    )
    user2 = models.ForeignKey(
        'Usuario',
        on_delete=models.CASCADE,
        related_name='conversations_received'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('user1', 'user2'),)

    @classmethod
    def get_or_create_conversation(cls, a, b):
        u1, u2 = (a, b) if a.id < b.id else (b, a)
        conv, _ = cls.objects.get_or_create(user1=u1, user2=u2)
        return conv



# chat/models.py

# models.py

class Mensagem(models.Model):
    visto_por = models.ManyToManyField('Usuario', blank=True, related_name='mensagens_vistas')
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='mensagens',
        null=True, blank=True
    )
    remetente = models.ForeignKey(
        'Usuario',
        on_delete=models.CASCADE,
        related_name='mensagens_enviadas'
    )
    destinatario = models.ForeignKey(
        'Usuario',
        on_delete=models.CASCADE,
        related_name='mensagens_recebidas'
    )
    conteudo = models.TextField(blank=True)
    audio = models.FileField(
        upload_to='audios/',
        blank=True,
        null=True
    )
    midia = models.FileField(            # <— novo campo
        upload_to='midias/',
        blank=True,
        null=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.remetente.nome} → {self.destinatario.nome}"



# chat/models.py
class Recado(models.Model):
    perfil = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    autor = models.CharField(max_length=100)
    foto = models.TextField(blank=True, null=True)
    texto = models.TextField()
    reacoes = models.CharField(max_length=20, blank=True)
    data = models.DateField(auto_now_add=True)
    left = models.IntegerField(default=0)
    top = models.IntegerField(default=0)
    z_index = models.IntegerField(default=1)

    def __str__(self):
        return f"Recado de {self.autor} para {self.perfil.nome}"


from django.db import models
from .models import Clube, Usuario  # certifique-se de importar seu modelo

from .models import Usuario  # ou ajuste conforme necessário

class Topico(models.Model):
    clube = models.ForeignKey(Clube, on_delete=models.CASCADE, related_name='topicos')
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    autor = models.CharField(max_length=100)  # string para simplificar

    arquivo_midia = models.FileField(upload_to='topicos_midias/', null=True, blank=True)

    def __str__(self):
        return self.titulo


class Resposta(models.Model):
    topico = models.ForeignKey(Topico, on_delete=models.CASCADE, related_name='respostas')
    autor = models.CharField(max_length=100)  # ou ForeignKey para Usuario, mas sem ser User do django
    conteudo = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)
    resposta_pai = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='respostas_filhas')

    def __str__(self):
        return f'Resposta de {self.autor} em "{self.topico.titulo}"'


class Sala(models.Model):
    clube = models.ForeignKey(Clube, on_delete=models.CASCADE, related_name='salas')
    nome = models.CharField(max_length=100)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} - {self.clube.nome}"


class SalaMensagem(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='mensagens')
    autor = models.CharField(max_length=100)  # ou autor = models.ForeignKey(Usuario, ...)
    texto = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.autor}: {self.texto[:30]}"

class SolicitacaoClube(models.Model):
    clube = models.ForeignKey(Clube, on_delete=models.CASCADE, related_name='solicitacoes')
    usuario_nome = models.CharField(max_length=100)
    criado_em = models.DateTimeField(auto_now_add=True)
    aprovado = models.BooleanField(default=False)
    rejeitado = models.BooleanField(default=False)
    foto_url = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('clube', 'usuario_nome')

    def __str__(self):
        return f"{self.usuario_nome} → {self.clube.nome}"

from django.db import models

class Evento(models.Model):
    clube = models.ForeignKey('Clube', on_delete=models.CASCADE, related_name='eventos')
    titulo = models.CharField(max_length=100)
    descricao = models.TextField()  # Agora obrigatório
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()  # Agora obrigatório
    banner = models.ImageField(upload_to='eventos_banners/', blank=True, null=True)  # Corrigido o caminho
    # Removido o campo criado_em

    def __str__(self):
        return f"{self.titulo} ({self.clube.nome})"




class Post(models.Model):
    clube = models.ForeignKey(Clube, on_delete=models.CASCADE)
    autor = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    imagem = models.ImageField(upload_to="posts/", blank=True, null=True)
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo


class Tema(models.Model):
    nome = models.CharField(max_length=100)
    ativo = models.BooleanField(default=False)
    imagem = models.ImageField(upload_to="temas/", blank=True, null=True)

    def __str__(self):
        return self.nome


class Novidade(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo

from django.db import models

class WPlaceState(models.Model):
    elements = models.JSONField(default=list)  # paths/erasers
    offset_x = models.FloatField(default=0)
    offset_y = models.FloatField(default=0)
    zoom = models.FloatField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
