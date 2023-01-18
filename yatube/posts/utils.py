from django.core.paginator import Paginator


def get_page_obj(post_list, posts_count, request):
    paginator = Paginator(post_list, posts_count)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
