import pytest

from app.modules.leitura_ia.arquivos import caminho_seguro, descobrir_tipo, salvar_foto, validar_foto
from app.nucleo.erros import DadosInvalidos

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 20


@pytest.mark.parametrize(("conteudo", "mime"), [(PNG, "image/png"), (JPEG, "image/jpeg"), (WEBP, "image/webp")])
def test_descobre_tipo_pelos_bytes(conteudo, mime):
    assert descobrir_tipo(conteudo) == mime


@pytest.mark.parametrize(
    "conteudo",
    [
        b"<script>alert(1)</script>",
        b"%PDF-1.7 ...",
        b"MZ\x90\x00",  # executável do Windows
        b"<svg xmlns='http://www.w3.org/2000/svg'/>",  # SVG pode carregar script
    ],
)
def test_recusa_o_que_nao_e_foto(conteudo):
    with pytest.raises(DadosInvalidos):
        validar_foto(conteudo, 1000)


def test_recusa_foto_grande_demais():
    with pytest.raises(DadosInvalidos):
        validar_foto(JPEG + b"\x00" * 2000, 1000)


def test_recusa_arquivo_vazio():
    with pytest.raises(DadosInvalidos):
        validar_foto(b"", 1000)


def test_salva_com_nome_aleatorio(tmp_path):
    nome1 = salvar_foto(tmp_path, JPEG, "image/jpeg")
    nome2 = salvar_foto(tmp_path, JPEG, "image/jpeg")
    assert nome1 != nome2 and nome1.endswith(".jpg")
    assert (tmp_path / nome1).read_bytes() == JPEG


@pytest.mark.parametrize("nome", ["../segredo.txt", "..\\..\\windows\\win.ini", "sub/pasta.jpg"])
def test_caminho_nao_sai_da_pasta_de_fotos(tmp_path, nome):
    with pytest.raises(DadosInvalidos):
        caminho_seguro(tmp_path, nome)
