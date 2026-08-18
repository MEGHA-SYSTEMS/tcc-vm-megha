from app.repositories..user_repositories import UserRepository
class AuthService:
    def __init__(self):
        self.user_repo= UserRepository()

        def register_user(self, nome: str, email: str, senha: str, confirma_senha: str):
            if not nome or not email or not senha:
                raise ValueError("Todos os campos são obrigatorios.")

                if senha != confirma_senha:
                    raise ValueError("As senhas não coincidem.")

                if len(senha) <6:
                    raise ValueError("A senha deve ter pelo menos 6 caracteres.")

                    try:
                        uid = self.user_repo.create_user_auth(email, senha, nome)

                        self.user_repo.save_user_data(uid, nome, email)

                        return True, "Conta criada com sucesso! Faça login para continuar."
                    except Exception as e:
                        raise Exception(f"Erro ao criar conta: {str(e)}")