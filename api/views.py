from django.contrib.auth.models import Group, User
from rest_framework import permissions, viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from .models import Company, Comment
from .serializers import CompanySerializer
from api.serializers import GroupSerializer, UserSerializer, CommentSerializer
from scraper.tasks import scrape_company_task
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny] 
    serializer_class = UserSerializer


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    @action(detail=False, methods=['get'], url_path='search')
    def search_company(self, request):
        url = request.query_params.get('url')
        print(url)
        if not url:
            return Response({'error': 'URL is required'}, status=400)

        try:
            company = Company.objects.get(url=url)

            if company.is_processed:
                serializer = self.get_serializer(company)
                return Response({'status': 'exists', 'company': serializer.data})
            else:
                return Response({
                    'status': 'processing',
                    'message': 'Scraping is already in progress.',
                    'slug': company.slug
                }, status=202)

        except Company.DoesNotExist:
            company = Company.objects.create(url=url, is_processed=False)

            scrape_company_task.delay(url)

            return Response({
                'status': 'processing',
                'message': 'Scraping started.',
                'slug': company.slug
            }, status=202)
        
class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        company = Company.objects.get(slug=self.kwargs['company_slug'])
        serializer.save(user=self.request.user, company=company)

    def get_queryset(self):
        return self.queryset.filter(company__slug=self.kwargs['company_slug'])

class CompanyBadgeWidgetView(TemplateView):
    template_name = "badge_embed.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = get_object_or_404(Company, id=kwargs['company_id'])
        context['company'] = company
        return context