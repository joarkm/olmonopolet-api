from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from .models import Beer
from stores.models import Store
from untappd.models import UserCheckIn, UserWishList
from django.db.models import F, Q, Max, OuterRef, Subquery
from .serializers import BeerSerializer
from rest_framework import generics
from django.views.generic import TemplateView
from django.utils import timezone

# Create your views here.

# View Functions
def beer_release(request):
    '''
    Return all beers which are to be released/launched in the future
    Paginated in order to use infinite scroll
    '''
    queryset = Beer.objects.filter(launch_date__gte=timezone.now()).order_by('launch_date', 'selection', 'name')
    paginator = Paginator(queryset, 50, 0)

    page_number = request.GET.get('page')
    beers = paginator.get_page(page_number)

    return render(request, 'stubs/beer_release.html', {'beers': beers})

def ordering_range_beers(request):
    '''
    Returns all beers in 'Bestillingsutvalet' at Vinmonopolet  
    Paginated in order to use infinite scroll  
    '''
    
    queryset = Beer.objects.filter(selection='Bestillingsutvalget',buyable=True, status='aktiv').order_by(F('untappd__rating').desc(nulls_last=True))
    
    if request.user.is_authenticated:
        
        # This subquery returns the rating of any beers the User has checked in to Untappd
        check_in_subquery = UserCheckIn.objects.filter(beer_id = OuterRef('beer_id'), user_id=request.user)
        queryset = queryset.annotate(untappd_rating=Subquery(check_in_subquery.values('rating')[:1]))

        # This subquery returns a value if User has the Beer in Wish List on Untappd
        wishlist_subquery = UserWishList.objects.filter(beer_id = OuterRef('beer_id'), user_id=request.user)
        queryset = queryset.annotate(untappd_wishlist=Subquery(wishlist_subquery.values('user')[:1]))

    paginator = Paginator(queryset, 50, 0)

    page_number = request.GET.get('page')
    beers = paginator.get_page(page_number)

    return render(request, 'stubs/ordering_range_beers.html', {'beers': beers, 'full_selection':True})

def ordering_range_search(request):
    '''
    Used by search bar in ordering range page (ordering_range)
    Returns a list of all matched beers in 'Bestillingsutvalet' at Vinmonopolet  
    PS: Search results are not paginated  
    '''

    # Check if query is empty
    if request.POST["query"] != '':
        # Fetch all Beers in stock at store 
        queryset = Beer.objects.filter(selection='Bestillingsutvalget',buyable=True, status='aktiv').order_by(F('untappd__rating').desc(nulls_last=True))
        # Find beers that match 'query' by name or brewery 
        queryset = queryset.filter(Q(name__icontains=request.POST["query"]) | Q(brewery__icontains=request.POST["query"]))
        
        if request.user.is_authenticated:
            # This subquery returns the rating of any beers the User has checked in to Untappd
            check_in_subquery = UserCheckIn.objects.filter(beer_id = OuterRef('beer_id'),user_id=request.user)
            queryset = queryset.annotate(untappd_rating=Subquery(check_in_subquery.values('rating')[:1]))

    else:
        # Returns all beers in 'Bestillingsutvalet' if query string is empty ('')
        return redirect('ordering_range_beers')
    return render(request, 'stubs/ordering_range_beers.html', {'beers': queryset, 'search':True, 'query':request.POST["query"]})

# Regular Views
class ReleaseListView(TemplateView):
    template_name = "release.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['store'] = Store.objects.get(store_id=self.kwargs['store_id'])
        return context

class OrderingRangeView(TemplateView):
    '''
    TemplateView presenting beers part of 'Bestillingsutvalet' at Vinmonopolet 
    '''
    template_name = "ordering_range.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['store'] = Store.objects.get(store_id=self.kwargs['store_id'])
        return context

# API Views
class BeerList(generics.ListAPIView):
    queryset=Beer.objects.all()
    serializer_class=BeerSerializer

class BeerDetail(generics.RetrieveAPIView):
    queryset = Beer.objects.all()
    serializer_class = BeerSerializer
