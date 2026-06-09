-- v3: compatibilidad match_face_embeddings con psycopg (text, real, integer explícitos)

create or replace function public.match_face_embeddings(
  in_org_id uuid,
  in_model text,
  in_embedding vector(512),
  in_threshold double precision default 0.35,
  in_match_count integer default 1
)
returns table (
  person_id text,
  full_name text,
  model text,
  distance real,
  confidence real
)
language sql
stable
as $$
  select
    e.person_id,
    p.full_name,
    e.model,
    (e.embedding <=> in_embedding)::real as distance,
    greatest(0, least(1, 1 - (e.embedding <=> in_embedding)))::real as confidence
  from public.face_embeddings e
  join public.persons p on p.person_id = e.person_id and p.org_id = e.org_id
  where e.org_id = in_org_id
    and e.model = in_model
    and (e.embedding <=> in_embedding) <= in_threshold::real
  order by e.embedding <=> in_embedding
  limit greatest(1, in_match_count);
$$;
