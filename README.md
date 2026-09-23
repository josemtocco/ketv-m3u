# KE TV → M3U automática

Projeto para gerar uma playlist M3U a partir dos canais públicos da KE TV:
https://www.ketv.com.br/canais

## O que faz

- Consulta periodicamente a página pública de canais da KE TV.
- Descobre as páginas individuais dos canais.
- Procura URLs HLS (`.m3u8`) expostas pelo próprio site.
- Valida os manifests HLS antes de incluí-los.
- Gera `ketv.m3u`.
- Remove automaticamente canais que deixarem de ser encontrados.
- Faz commit somente quando a playlist mudar.

> A disponibilidade dos streams depende da KE TV e dos respectivos provedores. O projeto não cria nem contorna autenticação; ele usa somente URLs públicas encontradas nas páginas consultadas.

## Instalação

1. Crie um repositório público no GitHub, por exemplo `ketv-m3u`.
2. Envie todos os arquivos deste projeto.
3. Vá em **Actions** e execute `Atualizar lista KE TV` manualmente uma vez.
4. Depois disso, o workflow será executado automaticamente a cada 6 horas.

## URL para SS IPTV

Depois do primeiro workflow concluído:

`https://raw.githubusercontent.com/SEU_USUARIO/ketv-m3u/main/ketv.m3u`

Substitua `SEU_USUARIO` pelo seu usuário do GitHub.

## Observação

A KE TV informa que seus canais usam HLS e que a grade é atualizada continuamente. Alguns canais podem ficar temporariamente offline por dependerem de provedores externos.
