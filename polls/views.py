from pathlib import Path
import joblib
from pandas import read_pickle
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Q, F, Sum
from django.db.models.functions import ExtractYear, ExtractMonth
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.http import JsonResponse, Http404, HttpResponseRedirect
from cart.cart import Cart
from cart.forms import CartAddProductForm
from teach import settings
# from cart.cart import Cart
from .models import Post, Recipe, Category, Product, ingredientItem, Visual, Question, Choice, PredResult
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .forms import CommentForm, RecipeCreateForm, LoginForm, PredictForm
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
# @login_required
from .utils import get_year_dict, months, colorPrimary
from django.shortcuts import render
from django.http import JsonResponse
import pickle
pickle_in = open('./savedModels/classifierModel.pkl', 'rb')
classifier = pickle.load(pickle_in)


def post_list(request):
    # ob_list = Post.objects.all()
    if request.method == 'POST':
        comment_form = PredictForm(data=request.POST)
        if comment_form.is_valid():
            comment_form.save()
    comment_form = PredictForm()
    latest_question_list = Question.objects.all()
    search_post = request.GET.get('search')
    visuals = Visual.objects.order_by('index').all()
    if search_post:
        posts = Post.objects.filter(Q(title=search_post))
    else:
        posts = Post.objects.all()
    paginator = Paginator(posts, 2)
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    return render(
        request,
        'post/list.html',
        {
            'page': page,
            'posts': posts,
            'section': 'post_list',
            'visuals': visuals,
            'latest_question_list': latest_question_list,
            'comment_form': comment_form
        }
    )


def post_detail(request, year, month, day, post):
    post = get_object_or_404(
        Post.objects.filter(slug=post),
        status='published',
        publish__year=year,
        publish__month=month,
        publish__day=day
    )
    comments = post.comments.filter(active=True)
    if request.method == 'POST':
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.save()
    comment_form = CommentForm()
    return render(
        request,
        'post/detail.html',
        {'post': post,
         'comments': comments,
         'comment_form': comment_form}
    )


def products(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    if category_slug:
        category = get_object_or_404(
            Category,
            slug=category_slug
        )
    return render(
        request,
        'post/products.html',
        {'category': category,
         'categories': categories,
         'products': products}
    )


def product_detail(request, id, slug):
    product = get_object_or_404(
        Product,
        id=id,
        slug=slug,
        available=True
    )
    return render(
        request,
        'post/card_detail.html',
        {'product': product}
    )


def product_detail(request, id, slug):
    product = get_object_or_404(Product,
                                id=id,
                                slug=slug,
                                available=True)
    cart_product_form = CartAddProductForm()
    return render(request, 'post/card_detail.html', {'product': product,
                                                     'cart_product_form': cart_product_form})


def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(
        Product,
        id=product_id
    )
    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        cart.add(product=product,
                 quantity=cd['quantity'],
                 update_quantity=cd['update'])
    return redirect('cart:cart_detail')


def recipe(request):
    recipes = Recipe.objects.all()
    if request.method == 'POST':
        recipe_create = RecipeCreateForm(data=request.POST)
        if request.user.is_authenticated:
            if recipe_create.is_valid():
                new_recipe_create = recipe_create.save(commit=False)
                new_recipe_create.author = request.user
                #
                new_recipe_create.save()
        else:
            return render(request, 'post/login.html')
    recipe_create = RecipeCreateForm()
    return render(request, 'post/price.html', {
        'recipes': recipes,
        'recipe_create': recipe_create
    })


def recipe_detail(request, id, title):
    recipe = get_object_or_404(
        Recipe,
        id=id,
        title=title
    )
    return render(
        request,
        'post/recipe_detail.html',
        {'recipe': recipe}
    )


def create_recipe(request):
    if request.method == 'POST':
        comment_form = RecipeCreateForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.save()
    comment_form = RecipeCreateForm()
    return render(
        request,
        'post/price.html',
        {'comment_form': comment_form}
    )


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(
                username=cd['username'],
                password=cd['password']
            )
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return render(
                        request,
                        'post/list.html'
                    )
                else:
                    # usering = User.objects.create_user(
                    #     username=cd['username'],
                    #     password=cd['password']
                    # )
                    # usering.save()
                    return HttpResponse('Disabled account')
                    # return render(
                    #     request,
                    #     'post/list.html'
                    # )
            else:
                usering = User.objects.create_user(
                    username=cd['username'],
                    password=cd['password']
                )
                usering.save()
                return render(
                    request,
                    'post/list.html'
                )
    else:
        form = LoginForm()
    return render(
        request,
        'post/login.html',
        {'form': form}
    )


def user_logout(request):
    logout(request)
    return render(request, 'post/login.html')


@staff_member_required
def get_filter_options(request):
    grouped_purchases = Product.objects.annotate(year=ExtractYear('created')).values('year').order_by('-year').distinct()
    options = [purchase['year'] for purchase in grouped_purchases]

    return JsonResponse({
        'options': options,
    })


@staff_member_required
def get_sales_chart(request, year):
    pro = Product.objects.filter(created__year=year)
    grouped_products = pro.annotate(pro_price=F('price'))\
        .annotate(month=ExtractMonth('created'))\
        .values('month').annotate(average=Sum('price'))\
        .values('month', 'average').order_by('month')

    sales_dict = get_year_dict()

    for group in grouped_products:
        sales_dict[months[group['month'] - 1]] = round(group['average'], 2)

    return JsonResponse({
        'title': f'Price in {year}',
        'data': {
            'labels': list(sales_dict.keys()),
            'datasets': [{
                'label': 'Amount ($)',
                'backgroundColor': colorPrimary,
                'borderColor': colorPrimary,
                'data': list(sales_dict.values())
            }]
        }
    })


# def index(request):
#     latest_question_list = Question.objects.all()
#     output = ', '.join([q.question_text for q in latest_question_list])
#     return HttpResponse(output)


def detail(request, question_id):
    try:
        question = Question.objects.get(pk=question_id)
    except Question.DoesNotExist:
        raise Http404("Question does not exist")
    return render(request, 'post/detail_question.html', {'question': question})


def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    try:
        selected_choice = question.choice_set.get(pk=request.POST['choice'])
    except (KeyError, Choice.DoesNotExist):
        return render(
            request,
            'post/detail_question.html', {
                'question': question,
                'error_message': "You didn't select a choice.",
            })
    else:
        selected_choice.votes += 1
        selected_choice.save()
        return HttpResponseRedirect(reverse('polls:results', args=(question.id,)))


def results(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    return render(request, 'post/results.html', {'question': question})


def prediction(sepal_length):
    prediction = classifier.predict(
        [[sepal_length]])
    print(prediction)
    return prediction


def home(request):
    res = ''
    if request.method == 'POST':
        sepal_length = float(request.POST.get('sepal_length'))
        result = prediction(sepal_length)
        if result == 0:
            res = 'Meat'
        elif result == 2:
            res = 'Cake'
        elif result == 1:
            res = 'Milk'
    return render(request, 'post/home.html', {'result': res})


# def predict_chances(request):
#     if request.POST.get('action') == 'post':
#         not_cat = request.POST.get('category')
#         category = 1
#         if not_cat == 'Tea'.lower():
#             category = 0
#         price = float(request.POST.get('price'))
#         model = read_pickle("new_model.pickle")
#         result = model.predict([[float(category), price]])
#         popular = result[0]
#         # if popular == 0.:
#         #     pop = 'low'
#         # elif popular == 1.:
#         #     pop = 'middle'
#         # elif popular == 2.:
#         #     pop = 'high'
#         PredResult.objects.create(category=category, price=price, popular=popular)
#         return JsonResponse({
#             'result': popular,
#             'category': category,
#             'price': price
#         })