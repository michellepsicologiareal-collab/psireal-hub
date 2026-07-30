-- Vincula respostas antigas ao login real da psi.
-- Rode uma vez depois de garantir que cada psi existe em public.psis.

update public.respostas_clinicas r
set psi_user_id = p.user_id
from public.psis p
where r.psi_user_id is null
  and r.psi_id is not null
  and r.psi_id = p.psi_id;

-- Conferencia: depois de rodar, este numero deve cair para 0
-- se todas as respostas antigas tiverem uma psi correspondente.
select count(*) as respostas_sem_psi_user_id
from public.respostas_clinicas
where psi_user_id is null;
