-- v7b: marca de envio real del correo con token

alter table public.employee_registration_tokens
  add column if not exists sent_at timestamptz;
